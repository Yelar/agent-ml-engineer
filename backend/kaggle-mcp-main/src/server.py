import json
# import os # No longer needed
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import mcp.types as types
# import asyncio # No longer explicitly needed here unless used elsewhere
# import uvicorn # No longer using uvicorn directly

# Define run_server function to encapsulate the logic
def run_server():
    load_dotenv()

    # Initialize Kaggle API
    api = None # Initialize api as None first
    try:
        api = KaggleApi()
        api.authenticate()
        print("Kaggle API Authenticated Successfully.")
    except Exception as e:
        print(f"Error authenticating Kaggle API: {e}")
        # api remains None if authentication fails

    # Initialize the FastMCP server
    mcp = FastMCP("kaggle-mcp")

    # --- Define Tools ---
    # Tools need access to 'api'. Define them inside run_server so they capture 'api' from the outer scope.
    @mcp.tool()
    async def search_kaggle_datasets(query: str) -> str:
        """Searches for datasets on Kaggle matching the query using the Kaggle API."""
        if not api:
            # Return an informative error if API is not available
            return json.dumps({"error": "Kaggle API not authenticated or available."})

        print(f"Searching datasets for: {query}")
        try:
            search_results = api.dataset_list(search=query)
            if not search_results:
                return "No datasets found matching the query."

            # Format results as JSON string for the tool output
            results_list = [
                {
                    "ref": getattr(ds, 'ref', 'N/A'),
                    "title": getattr(ds, 'title', 'N/A'),
                    "subtitle": getattr(ds, 'subtitle', 'N/A'),
                    "download_count": getattr(ds, 'downloadCount', 0), # Adjusted attribute name
                    "last_updated": str(getattr(ds, 'lastUpdated', 'N/A')), # Adjusted attribute name
                    "usability_rating": getattr(ds, 'usabilityRating', 'N/A') # Adjusted attribute name
                }
                for ds in search_results[:10]  # Limit to 10 results
            ]
            return json.dumps(results_list, indent=2)
        except Exception as e:
            # Log the error potentially
            print(f"Error searching datasets for '{query}': {e}")
            # Return error information as part of the tool output
            return json.dumps({"error": f"Error processing search: {str(e)}"})


    @mcp.tool()
    async def search_kaggle_competitions(query: str = "", status: str = "all") -> str:
        """Search Kaggle competitions by query and status.
        Args:
            query: Search term for competition title/description.
            status: Competition status ('all', 'active', 'completed'). Default 'all'.
        """
        if not api:
            return json.dumps({"error": "Kaggle API not authenticated or available."})

        print(f"Searching competitions for: '{query}' with status: {status}")
        try:
            # Map status to Kaggle API parameters
            status_map = {
                "active": "active",
                "completed": "completed", 
                "all": None
            }
            
            search_results = api.competition_list(search=query, category=status_map.get(status))
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
                    "user_has_entered": getattr(comp, 'userHasEntered', False)
                }
                for comp in search_results[:10]  # Limit to 10 results
            ]
            return json.dumps(results_list, indent=2)
        except Exception as e:
            print(f"Error searching competitions for '{query}': {e}")
            return json.dumps({"error": f"Error processing search: {str(e)}"})

    @mcp.tool()
    async def get_competition_details(competition_id: str) -> str:
        """Get comprehensive details about a Kaggle competition.
        Args:
            competition_id: The competition identifier (e.g., 'titanic').
        """
        if not api:
            return json.dumps({"error": "Kaggle API not authenticated or available."})

        print(f"Getting details for competition: {competition_id}")
        try:
            # Get basic competition info
            competition = api.competition_view(competition_id)
            
            # Get leaderboard info
            try:
                leaderboard = api.competition_leaderboard_view(competition_id)
                leaderboard_info = {
                    "submission_count": len(leaderboard),
                    "top_score": leaderboard[0].score if leaderboard else None
                }
            except:
                leaderboard_info = {"submission_count": 0, "top_score": None}

            details = {
                "id": competition_id,
                "title": getattr(competition, 'title', 'N/A'),
                "description": getattr(competition, 'description', 'N/A'),
                "evaluation_metric": getattr(competition, 'evaluationMetric', 'N/A'),
                "deadline": str(getattr(competition, 'deadline', 'N/A')),
                "category": getattr(competition, 'category', 'N/A'),
                "reward": getattr(competition, 'reward', 'N/A'),
                "team_count": getattr(competition, 'teamCount', 0),
                "user_has_entered": getattr(competition, 'userHasEntered', False),
                "url": f"https://www.kaggle.com/competitions/{competition_id}",
                "leaderboard_info": leaderboard_info
            }
            return json.dumps(details, indent=2)
        except Exception as e:
            print(f"Error getting competition details for '{competition_id}': {e}")
            return json.dumps({"error": f"Error getting competition details: {str(e)}"})

    @mcp.tool()
    async def download_competition_data(competition_id: str, download_path: str = None) -> str:
        """Download all competition files including datasets, sample submissions, and descriptions.
        Args:
            competition_id: The competition identifier (e.g., 'titanic').
            download_path: Optional path to download files. Defaults to 'competitions/<competition_id>'.
        """
        if not api:
            return json.dumps({"error": "Kaggle API not authenticated or available."})

        print(f"Downloading competition data for: {competition_id}")
        
        # Determine download path
        try:
            project_root = Path(__file__).parent.parent.resolve()
        except NameError:
            project_root = Path.cwd()

        if not download_path:
            download_path_obj = project_root / "competitions" / competition_id
        else:
            download_path_obj = project_root / Path(download_path)
            download_path_obj = download_path_obj.resolve()

        # Ensure download directory exists
        try:
            download_path_obj.mkdir(parents=True, exist_ok=True)
            print(f"Download directory: {download_path_obj}")
        except OSError as e:
            return json.dumps({"error": f"Error creating download directory '{download_path_obj}': {e}"})

        try:
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
            print(f"Error downloading competition data for '{competition_id}': {e}")
            if "404" in str(e):
                return json.dumps({"error": f"Competition '{competition_id}' not found or access denied."})
            return json.dumps({"error": f"Error downloading competition data: {str(e)}"})

    @mcp.tool()
    async def submit_to_competition(competition_id: str, submission_file_path: str, message: str = "") -> str:
        """Submit a CSV file to a Kaggle competition.
        Args:
            competition_id: The competition identifier (e.g., 'titanic').
            submission_file_path: Path to the CSV submission file.
            message: Optional submission message/description.
        """
        if not api:
            return json.dumps({"error": "Kaggle API not authenticated or available."})

        print(f"Submitting to competition: {competition_id}")
        print(f"Submission file: {submission_file_path}")

        # Validate submission file exists
        submission_path = Path(submission_file_path)
        if not submission_path.exists():
            return json.dumps({"error": f"Submission file not found: {submission_file_path}"})

        if not submission_path.suffix.lower() == '.csv':
            return json.dumps({"error": f"Submission file must be CSV format: {submission_file_path}"})

        try:
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
            print(f"Error submitting to competition '{competition_id}': {e}")
            return json.dumps({"error": f"Error submitting to competition: {str(e)}"})

    @mcp.tool()
    async def parse_kaggle_url(kaggle_url: str) -> str:
        """Extract competition ID from a Kaggle competition URL.
        Args:
            kaggle_url: Full Kaggle competition URL.
        """
        try:
            # Handle various URL formats
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
            
            return json.dumps({"error": f"Could not extract competition ID from URL: {kaggle_url}"})
            
        except Exception as e:
            return json.dumps({"error": f"Error parsing Kaggle URL: {str(e)}"})

    @mcp.tool()
    async def download_kaggle_dataset(dataset_ref: str, download_path: str | None = None) -> str:
        """Downloads files for a specific Kaggle dataset.
        Args:
            dataset_ref: The reference of the dataset (e.g., 'username/dataset-slug').
            download_path: Optional. The path to download the files to. Defaults to '<project_root>/datasets/<dataset_slug>'.
        """
        if not api:
            # Return an informative error if API is not available
            return json.dumps({"error": "Kaggle API not authenticated or available."})

        print(f"Attempting to download dataset: {dataset_ref}")

        # Determine absolute download path based on script location
        # Use Path.cwd() if run via script entry point, or __file__ if run directly
        try:
            project_root = Path(__file__).parent.parent.resolve() # NEW: this is the parent of src/, i.e., the project root
        except NameError: # __file__ might not be defined when run via entry point
            project_root = Path.cwd() # NEW: Assume cwd is project root if __file__ is not defined


        if not download_path:
            try:
                dataset_slug = dataset_ref.split('/')[1]
            except IndexError:
                return f"Error: Invalid dataset_ref format '{dataset_ref}'. Expected 'username/dataset-slug'."
            # Construct absolute path relative to project root
            download_path_obj = project_root / "datasets" / dataset_slug # NEW
        else:
            # If a path is provided, resolve it relative to project root
            download_path_obj = project_root / Path(download_path) # NEW
            # Ensure it's fully resolved
            download_path_obj = download_path_obj.resolve()


        # Ensure download directory exists (using the Path object)
        try:
            download_path_obj.mkdir(parents=True, exist_ok=True)
            print(f"Ensured download directory exists: {download_path_obj}") # Will print absolute path
        except OSError as e:
            return f"Error creating download directory '{download_path_obj}': {e}"

        try:
            print(f"Calling api.dataset_download_files for {dataset_ref} to path {str(download_path_obj)}")
            # Pass the path as a string to the Kaggle API
            api.dataset_download_files(dataset_ref, path=str(download_path_obj), unzip=True, quiet=False)
            return f"Successfully downloaded and unzipped dataset '{dataset_ref}' to '{str(download_path_obj)}'." # Show absolute path
        except Exception as e:
            # Log the error potentially
            print(f"Error downloading dataset '{dataset_ref}': {e}")
            # Check for 404 Not Found
            if "404" in str(e):
                return f"Error: Dataset '{dataset_ref}' not found or access denied."
            # Check for other specific Kaggle errors if needed
            return f"Error downloading dataset '{dataset_ref}': {str(e)}"


    # --- Define Prompts ---
    @mcp.prompt()
    async def generate_eda_notebook(dataset_ref: str) -> types.GetPromptResult:
        """Generates a basic EDA prompt for a given Kaggle dataset reference."""
        print(f"Generating EDA prompt for dataset: {dataset_ref}")
        prompt_text = f"Generate Python code for basic Exploratory Data Analysis (EDA) for the Kaggle dataset '{dataset_ref}'. Include loading the data, checking for missing values, visualizing key features, and basic statistics."
        return types.GetPromptResult(
            description=f"Basic EDA for {dataset_ref}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt_text),
                )
            ],
        )

    # --- Start the Server ---
    print("Starting Kaggle MCP Server via mcp.run()...")

    # Call the run() method on the FastMCP instance
    # This likely contains the server startup logic used by the CLI
    mcp.run()

    # The code below this point will only execute after mcp.run() stops
    print("Kaggle MCP Server stopped.")


# Standard boilerplate to run the server function when the script is executed directly
if __name__ == "__main__":
    # This block is less relevant now that we use `uv run kaggle-mcp`
    # which directly calls run_server(), but we keep it for potential direct execution
    print("Setting up and running Kaggle MCP Server (direct script run)...")
    run_server()
    # The mcp.run() call above will block, so messages below won't print until shutdown
    print("Server run finished (direct script run).")

# Remove the old print statement from the global scope
# print("Kaggle MCP Server defined. Run with 'mcp run server.py'")
