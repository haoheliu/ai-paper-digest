from flask import Flask, render_template, request, jsonify
import os
import json

app = Flask(__name__, static_folder="static")

# Directory for storing user data
USER_DATA_PATH = "/home/lxb/Disk_SSD/projects/ai-paper-digest/user_data"
os.makedirs(USER_DATA_PATH, exist_ok=True)

# Files for storing data
LIKED_PAPERS_FILE = os.path.join(USER_DATA_PATH, "liked_papers.json")
DISLIKED_PAPERS_FILE = os.path.join(USER_DATA_PATH, "disliked_papers.json")
PAPER_LISTS_FILE = os.path.join(USER_DATA_PATH, "paper_lists.json")

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
