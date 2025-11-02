"""
Dataset management and resolution
"""

from pathlib import Path
from typing import Optional
import pandas as pd

from .config import Config


class DatasetResolver:
    """Resolve dataset identifiers to file paths"""

    # Built-in dataset catalog
    CATALOG = {
        "sample_sales": "sample_sales.csv",
        "xau_intraday": "XAU_15m_data.csv",
        "office_train": "office_train.csv",
        "office_test": "office_test.csv",
    }

    @classmethod
    def resolve(cls, dataset_identifier: str) -> Path:
        """
        Resolve a dataset identifier to a file path

        Args:
            dataset_identifier: Dataset name or path

        Returns:
            Path to the dataset file

        Raises:
            FileNotFoundError: If dataset cannot be found
        """
        # Check if it's a built-in dataset
        if dataset_identifier in cls.CATALOG:
            path = Config.DATASETS_DIR / cls.CATALOG[dataset_identifier]
            if path.exists():
                return path
            raise FileNotFoundError(
                f"Built-in dataset '{dataset_identifier}' not found at {path}"
            )

        # Check if it's a direct path
        path = Path(dataset_identifier)
        if path.exists():
            return path

        # Check if it's relative to datasets directory
        path = Config.DATASETS_DIR / dataset_identifier
        if path.exists():
            return path

        raise FileNotFoundError(
            f"Dataset '{dataset_identifier}' not found. "
            f"Available built-in datasets: {list(cls.CATALOG.keys())}"
        )

    @classmethod
    def list_available(cls) -> list:
        """List all available datasets"""
        datasets = []

        # Add built-in datasets
        for name, filename in cls.CATALOG.items():
            path = Config.DATASETS_DIR / filename
            if path.exists():
                datasets.append({
                    'name': name,
                    'path': str(path),
                    'size': path.stat().st_size,
                    'builtin': True
                })

        # Add other CSV files in datasets directory
        if Config.DATASETS_DIR.exists():
            for csv_file in Config.DATASETS_DIR.glob("*.csv"):
                if csv_file.name not in cls.CATALOG.values():
                    datasets.append({
                        'name': csv_file.stem,
                        'path': str(csv_file),
                        'size': csv_file.stat().st_size,
                        'builtin': False
                    })

        return datasets


def load_dataset(dataset_path: Path) -> pd.DataFrame:
    """
    Load a dataset from a file path

    Args:
        dataset_path: Path to the dataset

    Returns:
        Loaded pandas DataFrame

    Raises:
        ValueError: If file format is not supported
    """
    if dataset_path.suffix.lower() == '.csv':
        return pd.read_csv(dataset_path)
    elif dataset_path.suffix.lower() in ['.xlsx', '.xls']:
        return pd.read_excel(dataset_path)
    elif dataset_path.suffix.lower() == '.parquet':
        return pd.read_parquet(dataset_path)
    elif dataset_path.suffix.lower() == '.json':
        return pd.read_json(dataset_path)
    else:
        raise ValueError(f"Unsupported file format: {dataset_path.suffix}")


def get_dataset_info(dataset_path: Path) -> dict:
    """
    Get comprehensive information about a dataset

    Args:
        dataset_path: Path to the dataset

    Returns:
        Dictionary with dataset information
    """
    df = load_dataset(dataset_path)

    info = {
        'name': dataset_path.stem,
        'path': str(dataset_path),
        'shape': df.shape,
        'columns': list(df.columns),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'missing_values': df.isnull().sum().to_dict(),
        'memory_usage': df.memory_usage(deep=True).sum(),
        'preview': df.head(5).to_dict('records')
    }

    # Add numeric column statistics
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        info['numeric_summary'] = df[numeric_cols].describe().to_dict()

    return info
