cd /home/lxb/Disk_SSD/projects/ai-paper-digest
uv run /home/lxb/Disk_SSD/projects/llm_pdf_reader/Arxiv/processes/refresh_database.py
git add .
git commit -m "refresh database $(date '+%Y-%m-%d %H:%M:%S')"
git push origin master