from django.core.management.base import BaseCommand
import djstripe.models
import stripe


class Command(BaseCommand):
    help = "Add 'legacy: True' metadata to all existing coupons"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get all coupons
        all_coupons = djstripe.models.Coupon.objects.all()

        self.stdout.write(f"Found {all_coupons.count()} total coupons")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for coupon in all_coupons:
            try:
                # Check if already marked as legacy
                if coupon.metadata.get("legacy") == "True":
                    self.stdout.write(f"  Skipping {coupon.name or coupon.id} - already marked as legacy")
                    skipped_count += 1
                    continue

                self.stdout.write(f"  Marking {coupon.name or coupon.id} ({coupon.id}) as legacy")

                if not dry_run:
                    # Update metadata in Stripe
                    updated_metadata = coupon.metadata.copy() if coupon.metadata else {}
                    updated_metadata["legacy"] = "True"
                    
                    stripe.Coupon.modify(
                        coupon.id,
                        metadata=updated_metadata,
                    )
                    
                    # Sync back to dj-stripe
                    djstripe.models.Coupon.sync_from_stripe_data(
                        stripe.Coupon.retrieve(coupon.id)
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f"    ✓ Marked as legacy"))
                else:
                    self.stdout.write(self.style.WARNING(f"    Would mark as legacy (dry run)"))

                updated_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  Error updating {coupon.id}: {str(e)}")
                )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN COMPLETE"))
            self.stdout.write(f"Would update: {updated_count} coupons")
        else:
            self.stdout.write(self.style.SUCCESS(f"UPDATE COMPLETE"))
            self.stdout.write(f"Updated: {updated_count} coupons")
        
        self.stdout.write(f"Skipped (already marked): {skipped_count} coupons")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count} coupons"))