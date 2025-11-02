"""
ML-specific tools for the agent
"""

from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool
import subprocess
import json
import os

from .datasets import get_dataset_info, load_dataset
from .python_executor import run_python_repl, format_execution_output
from .config import Config


@tool
def dataset_info(dataset_path: Annotated[str, "Path to the dataset file"]) -> str:
    """
    Get comprehensive information about a dataset including:
    - Shape (rows and columns)
    - Column names and data types
    - Missing values analysis
    - Numeric summary statistics
    - Data preview (first 5 rows)

    Use this before loading data to understand its structure.
    """
    try:
        info = get_dataset_info(Path(dataset_path))

        output = []
        output.append(f"Dataset: {info['name']}")
        output.append(f"Shape: {info['shape'][0]} rows × {info['shape'][1]} columns")
        output.append(f"\nColumns and Types:")

        for col, dtype in info['dtypes'].items():
            missing = info['missing_values'][col]
            missing_pct = (missing / info['shape'][0] * 100) if info['shape'][0] > 0 else 0
            output.append(f"  - {col}: {dtype} (missing: {missing}, {missing_pct:.1f}%)")

        if 'numeric_summary' in info:
            output.append(f"\nNumeric Columns Summary:")
            import pandas as pd
            summary_df = pd.DataFrame(info['numeric_summary'])
            output.append(summary_df.to_string())

        output.append(f"\nFirst 5 rows:")
        import pandas as pd
        preview_df = pd.DataFrame(info['preview'])
        output.append(preview_df.to_string())

        return "\n".join(output)

    except Exception as e:
        return f"Error getting dataset info: {str(e)}"


@tool
def execute_python(code: Annotated[str, "Python code to execute"]) -> str:
    """
    Execute Python code in a persistent namespace.

    - Variables and imports persist across calls
    - Dataset path(s) available as DATASET_PATH or DATASET_PATH_<NAME> variables
    - Plots (matplotlib/seaborn) automatically captured and saved
    - Execution timeout enforced for safety

    Use this to run any Python code: data loading, analysis, modeling, visualization, etc.
    """
    try:
        result = run_python_repl(code, timeout_seconds=Config.TIMEOUT_SECONDS)
        return format_execution_output(result)
    except Exception as e:
        return f"Error executing code: {str(e)}"


# Kaggle Competition Tools
@tool
def kaggle_search_competitions(
    query: Annotated[str, "Search term for competitions"] = "",
    status: Annotated[str, "Competition status: 'all', 'active', 'completed'"] = "all"
) -> str:
    """Search Kaggle competitions by query and status."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        
        # Map status to valid Kaggle API categories
        # Valid options: 'unspecified', 'featured', 'research', 'recruitment', 'gettingStarted', 'masters', 'playground'
        if status == "active":
            search_results = api.competitions_list(search=query)
        elif status == "completed":
            search_results = api.competitions_list(search=query)  
        else:  # "all" or any other value
            search_results = api.competitions_list(search=query)
        if not search_results:
            return "No competitions found matching the query."

        # Format results as JSON
        results_list = [
            {
                "ref": getattr(comp, 'ref', 'N/A'),
                "title": getattr(comp, 'title', 'N/A'),
                "description": getattr(comp, 'description', 'N/A')[:200] + "...",
                "url": f"https://www.kaggle.com/competitions/{getattr(comp, 'ref', '')}",
                "deadline": str(getattr(comp, 'deadline', 'N/A')),
                "category": getattr(comp, 'category', 'N/A'),
                "reward": getattr(comp, 'reward', 'N/A'),
                "team_count": getattr(comp, 'teamCount', 0),
            }
            for comp in search_results[:10]  # Limit to 10 results
        ]
        return json.dumps(results_list, indent=2)
    except Exception as e:
        return f"Error searching competitions: {str(e)}"


@tool
def kaggle_get_competition_details(competition_id: Annotated[str, "Competition identifier (e.g., 'titanic')"]) -> str:
    """Get comprehensive details about a Kaggle competition."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        
        # Get competition info using competitions_list with search
        competitions = api.competitions_list(search=competition_id)
        competition = None
        
        # Find exact match
        for comp in competitions:
            if competition_id in getattr(comp, 'ref', ''):
                competition = comp
                break
        
        if not competition and competitions:
            # Fallback to first result if no exact match
            competition = competitions[0]
        
        if not competition:
            return json.dumps({"error": f"Competition '{competition_id}' not found"})
        
        # Get leaderboard info
        try:
            leaderboard = api.competition_leaderboard_view(competition_id)
            leaderboard_info = {
                "submission_count": len(leaderboard) if leaderboard else 0,
                "top_score": leaderboard[0].score if leaderboard and len(leaderboard) > 0 else None
            }
        except Exception as e:
            leaderboard_info = {"submission_count": 0, "top_score": None, "error": str(e)}

        details = {
            "id": competition_id,
            "title": getattr(competition, 'title', 'N/A'),
            "description": getattr(competition, 'description', 'N/A'),
            "evaluation_metric": getattr(competition, 'evaluation_metric', 'N/A'),
            "deadline": str(getattr(competition, 'deadline', 'N/A')),
            "category": getattr(competition, 'category', 'N/A'),
            "reward": getattr(competition, 'reward', 'N/A'),
            "team_count": getattr(competition, 'team_count', 0),
            "user_has_entered": getattr(competition, 'user_has_entered', False),
            "url": f"https://www.kaggle.com/competitions/{competition_id}",
            "leaderboard_info": leaderboard_info
        }
        return json.dumps(details, indent=2)
    except Exception as e:
        return f"Error getting competition details: {str(e)}"


@tool
def kaggle_find_accessible_competition(
    query: Annotated[str, "Search query for competitions"] = "classification"
) -> str:
    """Find a Kaggle competition that's accessible without requiring rule acceptance.
    Args:
        query: Search term to find relevant competitions.
    """
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        import json
        api = KaggleApi()
        api.authenticate()
        
        # List of known accessible competitions (no rule acceptance needed)
        known_accessible = [
            "titanic",
            "digit-recognizer", 
            "house-prices-advanced-regression-techniques"
        ]
        
        print(f"Finding accessible competitions for query: {query}")
        
        # Try known accessible competitions first
        for comp_id in known_accessible:
            try:
                # Quick check - try to list files (lighter than download)
                files = api.competition_list_files(comp_id)
                if files:  # If we can list files, we have access
                    return json.dumps({
                        "success": True,
                        "competition_id": comp_id,
                        "message": f"Found accessible competition: {comp_id}",
                        "url": f"https://www.kaggle.com/competitions/{comp_id}",
                        "file_count": len(files)
                    })
            except Exception:
                continue
        
        return json.dumps({
            "success": False,
            "message": "Try these known accessible competitions: titanic, digit-recognizer",
            "suggestions": ["titanic", "digit-recognizer", "house-prices-advanced-regression-techniques"]
        })
        
    except Exception as e:
        return json.dumps({"error": f"Error finding accessible competition: {str(e)}"})


@tool
def kaggle_download_competition_data(
    competition_id: Annotated[str, "Competition identifier (e.g., 'titanic')"],
    download_path: Annotated[str, "Optional download path"] = None
) -> str:
    """Download all competition files including datasets, sample submissions, and descriptions."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        
        # Determine download path
        project_root = Path.cwd()
        if not download_path:
            download_path_obj = project_root / "competitions" / competition_id
        else:
            download_path_obj = Path(download_path).resolve()

        # Ensure download directory exists
        download_path_obj.mkdir(parents=True, exist_ok=True)
        
        # Download competition files
        api.competition_download_files(competition_id, path=str(download_path_obj), quiet=False)
        
        # List downloaded files
        downloaded_files = list(download_path_obj.rglob("*"))
        file_list = [str(f.relative_to(download_path_obj)) for f in downloaded_files if f.is_file()]
        
        result = {
            "success": True,
            "competition_id": competition_id,
            "download_path": str(download_path_obj),
            "downloaded_files": file_list,
            "file_count": len(file_list)
        }
        return json.dumps(result, indent=2)
        
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            # Try to automatically find an accessible competition as fallback
            print(f"403 error for {competition_id}, trying to find accessible alternative...")
            
            try:
                # Import the tool function we just created
                import asyncio
                
                # Known accessible competitions to try
                fallback_competitions = ["titanic", "digit-recognizer", "house-prices-advanced-regression-techniques"]
                
                for fallback_id in fallback_competitions:
                    if fallback_id == competition_id:
                        continue  # Don't try the same competition that failed
                        
                    try:
                        # Quick test - try to list files
                        files = api.competition_list_files(fallback_id)
                        if files:
                            print(f"Found accessible alternative: {fallback_id}")
                            
                            # Download the accessible competition instead
                            if not download_path:
                                fallback_download_path = project_root / "competitions" / fallback_id
                            else:
                                fallback_download_path = project_root / Path(download_path)
                            
                            fallback_download_path.mkdir(parents=True, exist_ok=True)
                            api.competition_download_files(fallback_id, path=str(fallback_download_path), quiet=False)
                            
                            # List downloaded files
                            downloaded_files = list(fallback_download_path.rglob("*"))
                            file_list = [str(f.relative_to(fallback_download_path)) for f in downloaded_files if f.is_file()]
                            
                            return json.dumps({
                                "success": True,
                                "auto_fallback": True,
                                "original_competition": competition_id,
                                "competition_id": fallback_id,
                                "download_path": str(fallback_download_path),
                                "downloaded_files": file_list,
                                "file_count": len(file_list),
                                "message": f"⚠️ '{competition_id}' requires rule acceptance. Automatically switched to accessible competition: '{fallback_id}'"
                            })
                    except Exception:
                        continue
                
                # If no fallbacks work, return helpful error
                return json.dumps({
                    "error": f"Access denied for competition '{competition_id}'. You may need to:",
                    "solutions": [
                        f"1. Go to https://www.kaggle.com/competitions/{competition_id} and accept the competition rules",
                        "2. Join the competition first before downloading data", 
                        "3. Use an accessible competition like 'titanic' instead"
                    ],
                    "accessible_alternatives": ["titanic", "digit-recognizer", "house-prices-advanced-regression-techniques"]
                })
                
            except Exception as fallback_error:
                return json.dumps({
                    "error": f"Access denied for '{competition_id}' and fallback failed: {str(fallback_error)}",
                    "solutions": [f"Try using: titanic, digit-recognizer, or house-prices-advanced-regression-techniques"]
                })
                
        elif "404" in str(e):
            return f"Error: Competition '{competition_id}' not found or access denied."
        return f"Error downloading competition data: {str(e)}"


@tool
def kaggle_submit_to_competition(
    competition_id: Annotated[str, "Competition identifier (e.g., 'titanic')"],
    submission_file_path: Annotated[str, "Path to the CSV submission file"],
    message: Annotated[str, "Optional submission message/description"] = ""
) -> str:
    """Submit a CSV file to a Kaggle competition."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        
        # Validate submission file exists
        submission_path = Path(submission_file_path)
        if not submission_path.exists():
            return f"Error: Submission file not found: {submission_file_path}"

        if not submission_path.suffix.lower() == '.csv':
            return f"Error: Submission file must be CSV format: {submission_file_path}"

        # Submit to competition
        result = api.competition_submit(
            file_name=str(submission_path), 
            message=message or f"Submission via ML Engineer Agent",
            competition=competition_id
        )
        
        return json.dumps({
            "success": True,
            "competition_id": competition_id,
            "submission_file": submission_file_path,
            "message": message,
            "result": str(result)
        }, indent=2)
        
    except Exception as e:
        return f"Error submitting to competition: {str(e)}"


@tool
def kaggle_parse_url(kaggle_url: Annotated[str, "Full Kaggle competition URL"]) -> str:
    """Extract competition ID from a Kaggle competition URL."""
    try:
        import re
        
        # Extract competition ID from URL
        patterns = [
            r'kaggle\.com/competitions/([^/?]+)',  # Standard format
            r'kaggle\.com/c/([^/?]+)',             # Short format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, kaggle_url)
            if match:
                competition_id = match.group(1)
                return json.dumps({
                    "success": True,
                    "competition_id": competition_id,
                    "url": kaggle_url
                })
        
        return f"Error: Could not extract competition ID from URL: {kaggle_url}"
        
    except Exception as e:
        return f"Error parsing Kaggle URL: {str(e)}"


def create_tool_list(kaggle_mode: bool = False):
    """Create the list of tools available to the agent"""
    base_tools = [dataset_info, execute_python]
    
    if kaggle_mode:
        kaggle_tools = [
            kaggle_search_competitions,
            kaggle_get_competition_details,
            kaggle_download_competition_data,
            kaggle_submit_to_competition,
            kaggle_parse_url,
            kaggle_find_accessible_competition
        ]
        return base_tools + kaggle_tools
    
    return base_tools
