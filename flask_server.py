from flask import Flask, render_template, request, jsonify
import os
import json
import math

app = Flask(__name__, static_folder="static")

# Directory for storing user data
USER_DATA_PATH = "/home/lxb/Disk_SSD/projects/ai-paper-digest/user_data"
os.makedirs(USER_DATA_PATH, exist_ok=True)

# Files for storing data
LIKED_PAPERS_FILE = os.path.join(USER_DATA_PATH, "liked_papers.json")
DISLIKED_PAPERS_FILE = os.path.join(USER_DATA_PATH, "disliked_papers.json")
PAPER_LISTS_FILE = os.path.join(USER_DATA_PATH, "paper_lists.json")

# Cache for main index to avoid repeated file reads
_main_index_cache = None
_main_index_cache_time = 0

def read_json(file_path, default_data=None):
    """Reads JSON from file, or returns default_data if missing."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return default_data if default_data is not None else {}

def write_json(file_path, data):
    """Writes data as JSON to file_path."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def get_main_index():
    """Get the main index with caching to improve performance."""
    global _main_index_cache, _main_index_cache_time
    import time
    
    current_time = time.time()
    # Cache for 5 minutes
    if _main_index_cache is None or (current_time - _main_index_cache_time) > 300:
        index_path = os.path.join(app.static_folder, "assets", "index.json")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                _main_index_cache = json.load(f)
                _main_index_cache_time = current_time
        else:
            _main_index_cache = {}
    
    return _main_index_cache

@app.route("/")
def index():
    """Serve the main HTML frontend."""
    return render_template("index.html")

@app.route("/get_data", methods=["GET"])
def get_data():
    """
    Returns all stored data from the server:
      - liked_papers: {paperId: likeCount}
      - disliked_papers: [paperId, ...]
      - paper_lists: {listName: [paperId, ...]}
    """
    liked_papers = read_json(LIKED_PAPERS_FILE, {})
    disliked_papers = read_json(DISLIKED_PAPERS_FILE, [])
    paper_lists = read_json(PAPER_LISTS_FILE, {})
    return jsonify({
        "liked_papers": liked_papers,
        "disliked_papers": disliked_papers,
        "paper_lists": paper_lists
    })

@app.route("/get_papers", methods=["GET"])
def get_papers():
    """
    Get papers for a specific category with pagination.
    Query parameters:
    - category: The paper category (e.g., "Arxiv-Sound", "Arxiv-CV")
    - page: Page number (1-based, default: 1)
    - per_page: Items per page (default: 10)
    - min_quality: Minimum quality filter (optional)
    - min_relevance: Minimum relevance filter (optional)
    - search: Search term in title/author (optional)
    - fields: Comma-separated list of fields to include (optional)
    """
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    min_quality = request.args.get("min_quality")
    min_relevance = request.args.get("min_relevance")
    search = request.args.get("search", "").lower().strip()
    fields_str = request.args.get("fields", "")
    
    if not category:
        return jsonify({"error": "Missing category parameter"}), 400
    
    # Get user data for filtering
    liked_papers = read_json(LIKED_PAPERS_FILE, {})
    disliked_papers = set(read_json(DISLIKED_PAPERS_FILE, []))
    paper_lists = read_json(PAPER_LISTS_FILE, {})
    readed_set = set(paper_lists.get("readed", []))
    
    # Get main index
    main_index = get_main_index()
    category_data = main_index.get(category, {})
    
    if not category_data:
        return jsonify({
            "papers": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        })
    
    # Parse fields filter
    selected_fields = set()
    if fields_str:
        selected_fields = set(fields_str.split(","))
    
    # Load and filter papers
    papers = []
    for paper_id, info in category_data.items():
        try:
            # Skip if paper is disliked
            if paper_id in disliked_papers:
                continue
                
            # Skip if paper is read (for non-Collected categories)
            if category != "Collected" and paper_id in readed_set:
                continue
            
            # Load paper data
            json_path = os.path.join(app.static_folder, "assets", info.get("json_path", ""))
            if not os.path.exists(json_path):
                continue
                
            with open(json_path, "r") as f:
                paper_data = json.load(f)
            
            # Apply filters
            if min_quality and (paper_data.get("quality", 0) < int(min_quality)):
                continue
            if min_relevance and (paper_data.get("relevance", 0) < int(min_relevance)):
                continue
            if selected_fields and paper_data.get("field") and paper_data.get("field") not in selected_fields:
                continue
            if search:
                combined_text = f"{paper_data.get('title', '')} {paper_data.get('author', '')}".lower()
                if search not in combined_text:
                    continue
            
            # Add paper to results
            papers.append({
                "id": paper_id,
                "info": {
                    "images": [info.get("first_image")] if info.get("first_image") else [],
                    "first_image": info.get("first_image")
                },
                "data": paper_data
            })
            
        except Exception as e:
            print(f"Error loading paper {paper_id}: {e}")
            continue
    
    # Sort papers (for Collected category, sort by likes)
    if category == "Collected":
        papers.sort(key=lambda x: liked_papers.get(x["id"], 0), reverse=True)
    else:
        # For other categories, sort by quality then relevance
        papers.sort(key=lambda x: (x["data"].get("quality", 0), x["data"].get("relevance", 0)), reverse=True)
    
    # Apply pagination
    total = len(papers)
    total_pages = math.ceil(total / per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_papers = papers[start_idx:end_idx]
    
    return jsonify({
        "papers": page_papers,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    })

@app.route("/get_collected_papers", methods=["GET"])
def get_collected_papers():
    """
    Get collected papers (liked papers from all categories) with pagination.
    This is a special endpoint for the "Collected" category.
    """
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    min_quality = request.args.get("min_quality")
    min_relevance = request.args.get("min_relevance")
    search = request.args.get("search", "").lower().strip()
    fields_str = request.args.get("fields", "")
    
    # Get user data
    liked_papers = read_json(LIKED_PAPERS_FILE, {})
    disliked_papers = set(read_json(DISLIKED_PAPERS_FILE, []))
    paper_lists = read_json(PAPER_LISTS_FILE, {})
    readed_set = set(paper_lists.get("readed", []))
    
    # Parse fields filter
    selected_fields = set()
    if fields_str:
        selected_fields = set(fields_str.split(","))
    
    # Get main index
    main_index = get_main_index()
    
    # Collect all papers from all categories
    all_papers = []
    for category, category_data in main_index.items():
        for paper_id, info in category_data.items():
            # Only include papers with likes > 0
            if (liked_papers.get(paper_id, 0) <= 0):
                continue
                
            # Skip if disliked
            if paper_id in disliked_papers:
                continue
            
            # Skip if read but not liked (for collected view)
            if paper_id in readed_set and (liked_papers.get(paper_id, 0) <= 0):
                continue
            
            try:
                # Load paper data
                json_path = os.path.join(app.static_folder, "assets", info.get("json_path", ""))
                if not os.path.exists(json_path):
                    continue
                    
                with open(json_path, "r") as f:
                    paper_data = json.load(f)
                
                # Apply filters
                if min_quality and (paper_data.get("quality", 0) < int(min_quality)):
                    continue
                if min_relevance and (paper_data.get("relevance", 0) < int(min_relevance)):
                    continue
                if selected_fields and paper_data.get("field") and paper_data.get("field") not in selected_fields:
                    continue
                if search:
                    combined_text = f"{paper_data.get('title', '')} {paper_data.get('author', '')}".lower()
                    if search not in combined_text:
                        continue
                
                # Add paper to results
                all_papers.append({
                    "id": paper_id,
                    "info": {
                        "images": [info.get("first_image")] if info.get("first_image") else [],
                        "first_image": info.get("first_image")
                    },
                    "data": paper_data
                })
                
            except Exception as e:
                print(f"Error loading paper {paper_id}: {e}")
                continue
    
    # Sort by likes (descending)
    all_papers.sort(key=lambda x: liked_papers.get(x["id"], 0), reverse=True)
    
    # Apply pagination
    total = len(all_papers)
    total_pages = math.ceil(total / per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_papers = all_papers[start_idx:end_idx]
    
    return jsonify({
        "papers": page_papers,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    })

@app.route("/like", methods=["POST"])
def like_paper():
    """
    Increments like count for a paper, or sets it if it doesn't exist.
    """
    data = request.json
    paper_id = data.get("paper_id")
    if not paper_id:
        return jsonify({"error": "Missing paper ID"}), 400

    liked_papers = read_json(LIKED_PAPERS_FILE, {})
    # Add +1 to like
    current_likes = liked_papers.get(paper_id, 0)
    new_likes = current_likes + 1
    liked_papers[paper_id] = new_likes
    write_json(LIKED_PAPERS_FILE, liked_papers)

    # If the paper is disliked, remove from disliked if new_likes >= 0
    # (Because if we 'like' something that was previously below zero, or considered disliked)
    disliked = set(read_json(DISLIKED_PAPERS_FILE, []))
    if paper_id in disliked and new_likes >= 0:
        disliked.remove(paper_id)
        write_json(DISLIKED_PAPERS_FILE, list(disliked))

    return jsonify({"message": "Paper liked", "likes": new_likes})

@app.route("/dislike", methods=["POST"])
def dislike_paper():
    """
    Decrements the like count by 1.
    If new like < 0 => truly disliked, stored in disliked_papers, removed from normal display.
    """
    data = request.json
    paper_id = data.get("paper_id")
    if not paper_id:
        return jsonify({"error": "Missing paper ID"}), 400

    liked_papers = read_json(LIKED_PAPERS_FILE, {})
    current_likes = liked_papers.get(paper_id, 0)
    new_likes = current_likes - 1  # subtract one
    liked_papers[paper_id] = new_likes
    write_json(LIKED_PAPERS_FILE, liked_papers)

    disliked = set(read_json(DISLIKED_PAPERS_FILE, []))
    # If new_likes < 0 => the paper is truly disliked
    if new_likes < 0:
        disliked.add(paper_id)
        write_json(DISLIKED_PAPERS_FILE, list(disliked))

    return jsonify({"message": "Dislike success", "likes": new_likes})

@app.route("/add_to_list", methods=["POST"])
def add_to_list():
    """Add a paper to a custom list in paper_lists."""
    data = request.json
    paper_id = data.get("paper_id")
    list_name = data.get("list_name")

    if not paper_id or not list_name:
        return jsonify({"error": "Missing paper ID or list name"}), 400

    paper_lists = read_json(PAPER_LISTS_FILE, {})
    if list_name not in paper_lists:
        paper_lists[list_name] = []
    if paper_id not in paper_lists[list_name]:
        paper_lists[list_name].append(paper_id)
    write_json(PAPER_LISTS_FILE, paper_lists)
    return jsonify({"message": f"Paper added to list {list_name}"})

@app.route("/mark_read", methods=["POST"])
def mark_read():
    """
    Mark a paper as read => add to 'readed' list in paper_lists.
    The paper is then removed from normal display.
    """
    data = request.json
    paper_id = data.get("paper_id")
    if not paper_id:
        return jsonify({"error": "Missing paper ID"}), 400

    paper_lists = read_json(PAPER_LISTS_FILE, {})
    if "readed" not in paper_lists:
        paper_lists["readed"] = []
    if paper_id not in paper_lists["readed"]:
        paper_lists["readed"].append(paper_id)
    write_json(PAPER_LISTS_FILE, paper_lists)

    return jsonify({"message": "Paper marked as read", "list": "readed"})

@app.route("/undo_dislike", methods=["POST"])
def undo_dislike():
    data = request.json
    paper_id = data.get("paper_id")
    if not paper_id:
        return jsonify({"error": "Missing paper ID"}), 400

    liked_papers = read_json(LIKED_PAPERS_FILE, {})
    disliked = set(read_json(DISLIKED_PAPERS_FILE, []))

    # reset likes to 0
    liked_papers[paper_id] = 0
    # remove from disliked
    if paper_id in disliked:
        disliked.remove(paper_id)

    write_json(LIKED_PAPERS_FILE, liked_papers)
    write_json(DISLIKED_PAPERS_FILE, list(disliked))

    return jsonify({"message": "Undo dislike success", "likes": 0})


@app.route("/unread", methods=["POST"])
def unread():
    data = request.json
    paper_id = data.get("paper_id")
    if not paper_id:
        return jsonify({"error": "Missing paper ID"}), 400

    paper_lists = read_json(PAPER_LISTS_FILE, {})
    if "readed" in paper_lists and paper_id in paper_lists["readed"]:
        paper_lists["readed"].remove(paper_id)

    write_json(PAPER_LISTS_FILE, paper_lists)
    return jsonify({"message": "Paper marked as unread"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)
