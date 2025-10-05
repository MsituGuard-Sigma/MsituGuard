from django.core.management.base import BaseCommand
from App.models import TreePlanting, Profile

class Command(BaseCommand):
    help = 'Calculate carbon credits for existing verified tree plantings'

    def handle(self, *args, **options):
        verified_trees = TreePlanting.objects.filter(
            status='verified',
            carbon_credits_calculated=False,
            planter__isnull=False
        )
        
        total_processed = 0
        total_credits = 0
        
        for tree_planting in verified_trees:
            try:
                # Set a default age for existing trees (assume 12 months)
                if tree_planting.tree_age_months == 0:
                    tree_planting.tree_age_months = 12
                    tree_planting.save()
                
                # Calculate carbon credits
                carbon_awarded = tree_planting.calculate_carbon_potential()
                
                if carbon_awarded:
                    total_processed += 1
                    total_credits += tree_planting.carbon_credits_potential
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'SUCCESS: {tree_planting.title}: {tree_planting.carbon_credits_potential:.3f} tonnes CO2'
                        )
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'ERROR: Error processing {tree_planting.title}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCarbon Credits Calculation Complete!\n'
                f'Processed: {total_processed} tree plantings\n'
                f'Total CO2: {total_credits:.3f} tonnes\n'
                f'Total Value: {total_credits * 500:.2f} KES'
            )
        )