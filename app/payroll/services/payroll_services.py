class PayrollService:
    """
    Services layer that coordinates payroll operations
    Follows Dependency Inversion principle
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def handle_line_creation(self, line_id):
        """Handle calculation after line creation"""
        self.orchestrator.recalculate_line(line_id, recalc_week=True)
    
    def handle_line_update(self, line_id, activity_changed=False):
        """Handle calculation after line update"""
        self.orchestrator.recalculate_line(line_id, recalc_week=activity_changed)
    
    def handle_line_deletion(self, worker, payroll_batch, date):
        """Handle calculation after line deletion"""
        self.orchestrator.recalculate_after_deletion(worker, payroll_batch, date)