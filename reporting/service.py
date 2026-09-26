from datetime import datetime, time, timedelta, timezone as datetime_timezone
from urllib.parse import urlencode

from django.db.models import Count, Exists, OuterRef
from django.utils import timezone

from cases.models import Case
from decisions.models import Decision
from identity.models import Delegation, Membership
from identity.policy import active_memberships, has_delegation, visible_cases, visible_intelligence
from inspections.models import Defense, ObservationSheet
from intelligence.models import Intelligence
from requests_app.models import CommunicationRequest, RequestResponse


DEFINITION_VERSION = "prototype-1"

# All periods are inclusive UTC calendar dates. The same queryset powers the
# aggregate and its drill-down; no independently maintained counter exists.
DEFINITIONS = {
    "requests.issued": ("Demandes émises", "Une demande par date réelle d'émission constatée.", "demandes"),
    "requests.responses": ("Réponses reçues", "Un courrier ou complément par date réelle de réception.", "reponses"),
    "sheets.created": ("Feuilles créées", "Une feuille par date d'enregistrement du brouillon.", "feuilles"),
    "sheets.defenses": ("Défenses reçues", "Un courrier ou complément par date réelle de réception.", "defenses"),
    "cases.classified": ("Dossiers classés sans suite", "Un dossier par décision de classement validée courante, selon sa date de validation.", "dossiers"),
    "cases.with_intelligence": ("Dossiers liés à un renseignement", "Un dossier créé dans la période et lié à au moins un renseignement visible ; ce lien ne prouve pas une causalité.", "dossiers"),
    "intelligence.received": ("Renseignements enregistrés", "Un renseignement par date d'enregistrement, même s'il est lié à plusieurs dossiers.", "renseignements"),
    "intelligence.linked_cases": ("Renseignements liés à un dossier", "Un renseignement enregistré dans la période et lié à au moins un dossier visible ; cette suite ne prouve pas un effet métier.", "renseignements"),
    "intelligence.distributed": ("Renseignements diffusés", "Un renseignement enregistré dans la période et diffusé au moins une fois ; plusieurs destinataires ne le doublent pas.", "renseignements"),
    "intelligence.with_returns": ("Renseignements avec retour", "Un renseignement enregistré dans la période et ayant au moins un retour d'une diffusion confirmée.", "renseignements"),
}

FAMILIES = (
    ("requests", ("requests.issued", "requests.responses")),
    ("sheets", ("sheets.created", "sheets.defenses")),
    ("classifications", ("cases.classified",)),
    ("pv", ()),
    ("intelligence", ("intelligence.received", "intelligence.linked_cases")),
)


def _bounds(start, end):
    return (
        timezone.make_aware(datetime.combine(start, time.min), datetime_timezone.utc),
        timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), datetime_timezone.utc),
    )


def rows_for(actor, unit, start, end, key, *, provenance=None):
    lower, upper = _bounds(start, end)
    cases = visible_cases(actor).filter(unit=unit)
    intelligence = visible_intelligence(actor).filter(unit=unit)
    if key == "requests.issued":
        return CommunicationRequest.objects.filter(case__in=cases, issuance__issued_at__gte=lower, issuance__issued_at__lt=upper).order_by("id")
    if key == "requests.responses":
        return RequestResponse.objects.filter(request__case__in=cases, received_on__range=(start, end)).order_by("id")
    if key == "sheets.created":
        return ObservationSheet.objects.filter(case__in=cases, created_at__gte=lower, created_at__lt=upper).order_by("id")
    if key == "sheets.defenses":
        return Defense.objects.filter(sheet__case__in=cases, received_on__range=(start, end)).order_by("id")
    if key == "cases.classified":
        superseding = Decision.objects.filter(replaces_id=OuterRef("pk"), state=Decision.State.VALIDATED)
        eligible = Decision.objects.filter(kind=Decision.Kind.CLASSIFICATION, state=Decision.State.VALIDATED, validated_at__gte=lower, validated_at__lt=upper).annotate(superseded=Exists(superseding)).filter(superseded=False)
        return cases.filter(decisions__in=eligible).distinct().order_by("id")
    if key == "cases.with_intelligence":
        return cases.filter(created_at__gte=lower, created_at__lt=upper, intelligence__in=intelligence).distinct().order_by("id")
    if key == "intelligence.received":
        result = intelligence.filter(created_at__gte=lower, created_at__lt=upper)
    elif key == "intelligence.linked_cases":
        result = intelligence.filter(created_at__gte=lower, created_at__lt=upper, cases__in=cases).distinct()
    elif key == "intelligence.distributed":
        result = intelligence.filter(created_at__gte=lower, created_at__lt=upper, disseminations__sent_at__isnull=False).distinct()
    elif key == "intelligence.with_returns":
        result = intelligence.filter(created_at__gte=lower, created_at__lt=upper, disseminations__sent_at__isnull=False, disseminations__returns__isnull=False).distinct()
    else:
        raise KeyError(key)
    return result.filter(provenance=provenance).order_by("id") if provenance is not None else result.order_by("id")


def detail_url(key, unit, start, end, *, provenance=None):
    params = {"unit": str(unit.pk), "start": start.isoformat(), "end": end.isoformat()}
    if provenance is not None:
        params["provenance"] = provenance
    return f"/api/v1/statistiques/{key}/?{urlencode(params)}"


def indicator(actor, unit, start, end, key, *, provenance=None, value=None):
    label, definition, _ = DEFINITIONS[key]
    if value is None:
        value = rows_for(actor, unit, start, end, key, provenance=provenance).count()
    result = {"key": key, "label": label, "definition": definition, "definition_version": DEFINITION_VERSION, "value": value, "detail_url": detail_url(key, unit, start, end, provenance=provenance), "status": "available"}
    if provenance is not None:
        result["provenance"] = provenance
    return result


def masked(key, label, reason):
    return {"key": key, "label": label, "definition": reason, "definition_version": DEFINITION_VERSION, "value": None, "detail_url": None, "status": "masked", "reason": reason}


def can_read_distribution(actor, unit):
    return active_memberships(actor, unit=unit).filter(role=Membership.Role.MANAGER).exists() and has_delegation(actor, Delegation.Action.INTELLIGENCE_DISTRIBUTE, unit)


def dashboard(actor, unit, start, end):
    families = []
    for family_key, keys in FAMILIES:
        indicators = [indicator(actor, unit, start, end, key) for key in keys]
        if family_key == "sheets":
            indicators.append(masked("sheets.issued", "Feuilles émises ou notifiées", "Aucun constat d'émission ou de notification de feuille n'est enregistré."))
        if family_key == "pv":
            indicators.append(masked("cases.pv_proven", "Dossiers avec PV établi", "La preuve et la référence du PV restent à définir par la DGDA (DEC-04). Une orientation ou transmission GELEC ne suffit pas."))
        if family_key == "intelligence":
            indicators.append(indicator(actor, unit, start, end, "cases.with_intelligence"))
            groups = rows_for(actor, unit, start, end, "intelligence.received").order_by().values("provenance").annotate(total=Count("pk", distinct=True)).order_by("provenance")
            indicators.extend(indicator(actor, unit, start, end, "intelligence.received", provenance=group["provenance"], value=group["total"]) for group in groups)
            if can_read_distribution(actor, unit):
                indicators.extend(indicator(actor, unit, start, end, key) for key in ("intelligence.distributed", "intelligence.with_returns"))
            else:
                indicators.extend(masked(key, DEFINITIONS[key][0], "Délégation de diffusion requise pour ce décompte.") for key in ("intelligence.distributed", "intelligence.with_returns"))
            indicators.append(masked("intelligence.effects", "Effets obtenus", "Les catégories et preuves d'effet doivent être définies par la DGDA ; un dossier ouvert n'est qu'une suite documentée."))
        for item in indicators:
            item.update(unit=unit.pk, start=start, end=end)
        families.append({"key": family_key, "indicators": indicators})
    return {"unit": unit.pk, "start": start, "end": end, "definition_version": DEFINITION_VERSION, "prototype_only": True, "families": families}


def object_url(key, identifier):
    return f"/api/v1/{DEFINITIONS[key][2]}/{identifier}/"
