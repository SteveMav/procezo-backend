from django.db import migrations


def backfill_classification(apps, schema_editor):
    AuditEvent = apps.get_model("audit", "AuditEvent")
    Case = apps.get_model("cases", "Case")
    alias = schema_editor.connection.alias
    events = AuditEvent.objects.using(alias).filter(resource_type="case", resource_id__isnull=False).only("id", "resource_id")
    for event in events.iterator(chunk_size=200):
        classification = Case.objects.using(alias).filter(pk=event.resource_id).values_list("classification", flat=True).first()
        # An orphaned reference is treated as restricted for audit visibility.
        AuditEvent.objects.using(alias).filter(pk=event.pk).update(classification=1 if classification is None else classification)


class Migration(migrations.Migration):
    dependencies = [("audit", "0002_auditevent_classification"), ("cases", "0001_initial")]
    operations = [migrations.RunPython(backfill_classification, migrations.RunPython.noop)]
