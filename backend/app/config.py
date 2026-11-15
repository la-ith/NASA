"""Private local configuration; explicit process settings always take precedence."""
import os
from pathlib import Path
from dotenv import dotenv_values


def load_private_env(path=None):
    path=Path(path) if path else Path(__file__).resolve().parents[1]/'.env'
    # Disable ${...} interpolation: a credential is a literal value, never a template or shell command.
    for name,value in dotenv_values(path,interpolate=False).items():
        if value and name in {'OPENAI_API_KEY','OPENAI_MODEL','CIMIS_APP_KEY','FIELD_SHIFT_AI_DAILY_CALL_LIMIT',
                              'FIELD_SHIFT_LAYER_DIR','FIELD_SHIFT_DB','FIELD_SHIFT_EXPERT_KEY',
                              'FIELD_SHIFT_ALLOWED_ORIGINS','FIELD_SHIFT_COOKIE_SECURE'}:
            os.environ.setdefault(name,value)
