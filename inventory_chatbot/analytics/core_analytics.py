import logging
import pandas as pd
from typing import Dict
from fastapi import UploadFile

logger = logging.getLogger(__name__)

SESSION_DATASETS: Dict[str, pd.DataFrame] = {}


def load_dataset_for_session(file: UploadFile, session_id: str) -> pd.DataFrame:
    logger.debug(f"Uploading file for session: {session_id}")

    df = pd.read_csv(file.file)
    SESSION_DATASETS[session_id] = df

    logger.info(f"Successfully loaded dataset for session {session_id}. Active sessions: {list(SESSION_DATASETS.keys())}")

    return df


def get_session_dataframe(session_id: str) -> pd.DataFrame | None:
    logger.debug(f"Retrieving dataframe for session: {session_id}")

    df = SESSION_DATASETS.get(session_id)

    if df is None:
        logger.warning(f"No dataset found for session: {session_id}")
    else:
        logger.info(f"Dataset found for session: {session_id}")

    return df
