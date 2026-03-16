"""
seed_lab_data — Populate the Lab module with sample tests, orders, samples, and results.

Usage:  python manage.py seed_lab_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import uuid
import random


# ── Lab Test definitions ──────────────────────────────────────────────
LAB_TESTS = [
    {
        "name": "Complete Blood Count (CBC)",
        "code": "CBC-001",
        "category": "Hematology",
        "reference_range": "4.5-11.0",
        "sample_type": "Blood",
        "preparation_instructions": "No special preparation required",
        "turnaround_time": "24 hours",
        "price": 350,
    },
    {
        "name": "Lipid Panel",
        "code": "LIP-001",
        "category": "Biochemistry",
        "reference_range": "LDL < 100, HDL > 40, Total < 200",
        "sample_type": "Blood",
        "preparation_instructions": "Fasting for 12 hours before sample collection",
        "turnaround_time": "24 hours",
        "price": 600,
    },
    {
        "name": "Thyroid Profile (T3, T4, TSH)",
        "code": "THY-001",
        "category": "Endocrinology",
        "reference_range": "TSH: 0.4-4.0",
        "sample_type": "Blood",
        "preparation_instructions": "Early morning sample preferred",
        "turnaround_time": "48 hours",
        "price": 800,
    },
    {
        "name": "Fasting Blood Sugar",
        "code": "FBS-001",
        "category": "Biochemistry",
        "reference_range": "70-110",
        "sample_type": "Blood",
        "preparation_instructions": "Fasting for 8-12 hours",
        "turnaround_time": "6 hours",
        "price": 150,
    },
    {
        "name": "Urinalysis",
        "code": "URI-001",
        "category": "Clinical Pathology",
        "reference_range": "pH: 4.5-8.0",
        "sample_type": "Urine",
        "preparation_instructions": "Collect midstream urine sample",
        "turnaround_time": "12 hours",
        "price": 200,
    },
    {
        "name": "Liver Function Test (LFT)",
        "code": "LFT-001",
        "category": "Biochemistry",
        "reference_range": "ALT: 7-56, AST: 10-40",
        "sample_type": "Blood",
        "preparation_instructions": "Fasting for 8 hours",
        "turnaround_time": "24 hours",
        "price": 700,
    },
    {
        "name": "Kidney Function Test (KFT)",
        "code": "KFT-001",
        "category": "Biochemistry",
        "reference_range": "Creatinine: 0.7-1.3",
        "sample_type": "Blood",
        "preparation_instructions": "No special preparation required",
        "turnaround_time": "24 hours",
        "price": 650,
    },
    {
        "name": "Vitamin D (25-Hydroxy)",
        "code": "VTD-001",
        "category": "Immunology",
        "reference_range": "30-100",
        "sample_type": "Blood",
        "preparation_instructions": "No special preparation required",
        "turnaround_time": "48 hours",
        "price": 1200,
    },
]

# Order scenarios with statuses
ORDER_SCENARIOS = [
    {"status": "PENDING", "priority": "ROUTINE", "hours_ago": 2},
    {"status": "PENDING", "priority": "URGENT", "hours_ago": 1},
    {"status": "COLLECTED", "priority": "ROUTINE", "hours_ago": 6},
    {"status": "PROCESSING", "priority": "ROUTINE", "hours_ago": 12},
    {"status": "COMPLETED", "priority": "ROUTINE", "hours_ago": 20},
]


class Command(BaseCommand):
    help = "Seed lab tests, orders, samples, and results with sample data."

    def handle(self, *args, **options):
        from apps.labs.models import LabTest, LabOrder, LabSample, LabResult
        from apps.patients.models import Patient
        from apps.billing.models import Invoice, InvoiceItem
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # ── 1. Create Lab Tests ──
        created_tests = 0
        tests = []
        for data in LAB_TESTS:
            test, created = LabTest.objects.update_or_create(
                code=data["code"],
                defaults=data,
            )
            tests.append(test)
            if created:
                created_tests += 1
        self.stdout.write(
            f"  Lab Tests: {created_tests} created, {len(LAB_TESTS) - created_tests} updated"
        )

        # ── 2. Check prerequisites ──
        patients = list(Patient.objects.all()[:5])
        if not patients:
            self.stdout.write(self.style.WARNING(
                "  ⚠ No patients found. Please create at least one patient first."
            ))
            return

        doctors = list(User.objects.filter(is_superuser=True)[:2])
        if not doctors:
            doctors = list(User.objects.all()[:1])

        # ── 3. Create Lab Orders with different statuses ──
        created_orders = 0
        now = timezone.now()

        for i, scenario in enumerate(ORDER_SCENARIOS):
            patient = patients[i % len(patients)]
            doctor = doctors[i % len(doctors)] if doctors else None

            ordered_at = now - timedelta(hours=scenario["hours_ago"])

            order = LabOrder.objects.create(
                patient=patient,
                doctor=doctor,
                status=scenario["status"],
                priority=scenario["priority"],
                notes=f"Seed order #{i+1} — {scenario['status']}",
            )
            # Manually set ordered_at to simulate realistic timelines
            LabOrder.objects.filter(id=order.id).update(ordered_at=ordered_at)
            order.refresh_from_db()

            # Assign 1-3 random tests
            order_tests = random.sample(tests, min(random.randint(1, 3), len(tests)))
            order.tests.set(order_tests)
            created_orders += 1

            # ── 4. Create LabSample for collected+ orders ──
            if scenario["status"] in ("COLLECTED", "PROCESSING", "COMPLETED", "REPORT_UPLOADED"):
                sample_types = list(set(t.sample_type for t in order_tests if t.sample_type))
                for si, stype in enumerate(sample_types):
                    LabSample.objects.create(
                        order=order,
                        sample_type=stype,
                        collection_location="Lab Counter A",
                        collected_at=ordered_at + timedelta(hours=1),
                        collected_by=doctor,
                        barcode=f"LAB-{order.id.hex[:8].upper()}-{si}-{uuid.uuid4().hex[:4].upper()}",
                    )

            # ── 5. Create LabResult for completed orders ──
            if scenario["status"] in ("COMPLETED", "REPORT_UPLOADED"):
                for test in order_tests:
                    # Generate a realistic value — sometimes abnormal
                    is_abnormal = random.random() < 0.3  # 30% chance abnormal
                    if test.code == "FBS-001":
                        value = str(random.randint(60, 140))
                    elif test.code == "CBC-001":
                        value = str(round(random.uniform(3.0, 14.0), 1))
                    elif test.code == "VTD-001":
                        value = str(round(random.uniform(10, 90), 1))
                    else:
                        value = str(round(random.uniform(5, 120), 1))

                    LabResult.objects.create(
                        order=order,
                        test=test,
                        value=value,
                        is_abnormal=is_abnormal,
                        recorded_by=doctor,
                    )

                # Mark updated_at to simulate completion within TAT
                completion_time = ordered_at + timedelta(hours=random.randint(4, 22))
                LabOrder.objects.filter(id=order.id).update(updated_at=completion_time)

            # ── 6. Billing integration ──
            total_price = sum(t.price for t in order_tests)
            if total_price > 0:
                invoice = Invoice.objects.create(
                    patient=patient,
                    status='DRAFT',
                    created_by=doctor,
                    notes=f"Auto-generated for Lab Order {order.id.hex[:8].upper()}"
                )
                for test in order_tests:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=f"Lab Test: {test.name}",
                        quantity=1,
                        unit_price=test.price,
                    )
                invoice_items = invoice.items.all()
                invoice.subtotal = sum(item.total for item in invoice_items)
                invoice.grand_total = invoice.subtotal
                invoice.save()

        self.stdout.write(f"  Lab Orders: {created_orders} created with samples, results, and invoices")
        self.stdout.write(self.style.SUCCESS("\n✅ Lab seed data created successfully!"))
