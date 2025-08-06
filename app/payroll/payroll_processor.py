from dataclasses import dataclass
from typing import List
import pandas as pd
from .models import (
    FieldWorker, 
    Activity,
    PayrollBatchLine
)


@dataclass
class ValidationError:
    row_number: int
    message: str

    def __str__(self) -> str:
        return f"Row {self.row_number}: {self.message}"

class PayrollFileValidator:
    """Handles validation of payroll file data"""

    def __init__(self, required_columns=None, valid_workers=None, valid_activities=None):
        self.required_columns = required_columns or {"date", 'field_worker', 'activity', 'quantity'}
        self._valid_workers = valid_workers
        self._valid_activities = valid_activities
    
    def _load_reference_data(self):
        """Load reference data once for validation"""
        if self._valid_workers is None:
            self._valid_workers = set(
                FieldWorker.objects.values_list('identification_number', flat=True)
            )
        if self._valid_activities is None:
            self._valid_activities = set(
                Activity.objects.values_list('name', flat=True)
            )

    def validate_structure(self, df: pd.DataFrame) -> List[ValidationError]:
        """Validate Dataframe structure and required columns"""
        errors = []
        # Check required columns
        missing_cols = self.required_columns - set(df.columns)
        if missing_cols:
            errors.append(ValidationError(0, f"Missing required columns: {missing_cols}"))
        
        return errors

    def validate_data(self, df: pd.DataFrame) -> List[ValidationError]:
        """Validate data content row by row"""
        self._load_reference_data()
        errors = []
        
        for idx, row in df.iterrows():
            row_num = idx + 2 # Account for header row and 0-indexing

            # Check for blank required fields
            if pd.isna(row["date"]) or pd.isna(row["field_worker"]) or \
            pd.isna(row["activity"]) or pd.isna(row["quantity"]):
                errors.append(ValidationError(row_num, "One of the required fields is blank"))
                continue

            # Validate references
            if row['field_worker'] not in self._valid_workers:
                errors.append(ValidationError(row_num, f"Invalid field worker: {row['field_worker']}"))
            if row['activity'] not in self._valid_activities:
                errors.append(ValidationError(row_num, f"Invalid activity: {row['activity']}"))

        return errors

class PayrollFileProcessor:
    """Handles reading and cleaning of payroll files"""

    @staticmethod
    def read_file(file_path: str) -> pd.DataFrame:
        """Reads CSV or Excel fil into a DataFrame"""
        if file_path.endswith(('.xls', '.xlsx')):
            return pd.read_excel(file_path, dtype={"field_worker": str})
        else:
            return pd.read_csv(file_path, dtype={"field_worker": str})
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and prepare data from file"""
        df.columns = df.columns.str.strip().str.lower()

        # Convert date column to proper format
         # 1) parse your date‐column into actual datetimes:
        df['date'] = pd.to_datetime(
            df['date'],
            format="%Y-%m-%d",   # ← change this to whatever your incoming format is,
            errors="raise"       # or 'coerce' if you want invalid → NaT
        )

        df = df.drop_duplicates()

        return df

class PayrollBatchCreator:
    """Handles bulk creation of PayrollBatchLine objects"""

    def __init__(self, batch_size=500):
        self.batch_size = batch_size
        self._field_workers_cache = None
        self._activities_cache = None
    
    def _load_refences_objects(self):
        """Load full object for foreign key relationships"""
        if self._field_workers_cache is None:
            self._field_workers_cache = {
                fw.identification_number: fw for fw in FieldWorker.objects.all()
            }
        if self._activities_cache is None:
            self._activities_cache = {
                a.name: a for a in Activity.objects.all()
            }

    def _create_batch_lines(self, batch, df):
        """Create PayrollBatchLine objects in batches"""
        self._load_refences_objects()
        
        lines = []

        for row in df.itertuples(index=False):
            try:
                # Bulk creat bypasses model's save method
                # set the iso_week and iso_year
                year, week, _ = row.date.isocalendar()

                lines.append(
                    PayrollBatchLine(
                        payroll_batch=batch,
                        date=row.date,
                        field_worker=self._field_workers_cache[row.field_worker],
                        activity=self._activities_cache[row.activity],
                        quantity=row.quantity,
                        iso_week=week,
                        iso_year=year
                    )
                )

                if len(lines) >= self.batch_size:
                    PayrollBatchLine.objects.bulk_create(lines)
                    lines.clear()

            except KeyError as e:
                batch.error_message = str(e)
                raise Exception(f"Reference not found: {e}")

        if lines:
            PayrollBatchLine.objects.bulk_create(lines)