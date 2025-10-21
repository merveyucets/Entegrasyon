import csv
import requests
import os
from datetime import datetime
from dateutil import parser
from dotenv import load_dotenv
load_dotenv()  # .env dosyasını oku

# --------------- AYARLAR ----------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

REPO = "merveyucets/Entegrasyon"  # Repo adı
PROJECT_ID = "PVT_kwHOB0hXU84BFtV0"

# ProjectV2 alan id'leri
FIELDS = {
    "Status": "PVTSSF_lAHOB0hXU84BFtV0zg296Bw",
    "Priority": "PVTSSF_lAHOB0hXU84BFtV0zg296Dg",
    "Estimate": "PVTF_lAHOB0hXU84BFtV0zg296Do",
    "StartDate": "PVTF_lAHOB0hXU84BFtV0zg296Ds",
    "EndDate": "PVTF_lAHOB0hXU84BFtV0zg296Dw",
    "Size": "PVTF_lAHOB0hXU84BFtV0zg2-DjI",
    "Milestone": "PVTSSF_MILESTONE_ID",
    "Development": "PVTSSF_DEVELOPMENT_ID",
    "Assignee": "PVTSSF_ASSIGNEE_ID"
}

# Option id eşleşmeleri
OPTION_IDS = {
    "Status": {
        "Backlog": "f75ad846",
        "Ready": "61e4505c",
        "In progress": "47fc9ee4",
        "In review": "df73e18b",
        "Done": "98236657"
    },
    "Priority": {
        "Lowest": "79628723",
        "Low": "0a877460",
        "Medium": "da944a9c",
        "Highest": "ac7add12"
    },
    "Milestone": {
        # Örnek: "Sprint 1": "xxx"
    }
}

# Jira kullanıcı adlarını GitHub kullanıcı adlarına eşleme
ASSIGNEE_MAP = {
    "affan.bugra.ozaytas": "affanbaykar",
    "merve.yucetas" : "merveyucets"
    # gerekiyorsa diğer kullanıcıları ekle
}

# --------------- HELPER FUNCTIONS ----------------
def run_graphql(query, variables):
    url = "https://api.github.com/graphql"
    r = requests.post(url, headers=HEADERS, json={"query": query, "variables": variables})
    if r.status_code != 200:
        print("GraphQL Hata:", r.status_code, r.text)
        return None
    return r.json()

def add_item_to_project(issue_node_id):
    query = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input:{projectId:$projectId, contentId:$contentId}) {
        item { id }
      }
    }
    """
    variables = {"projectId": PROJECT_ID, "contentId": issue_node_id}
    result = run_graphql(query, variables)
    if result and result.get("data"):
        return result["data"]["addProjectV2ItemById"]["item"]["id"]
    return None

def update_project_field(item_id, field_id, value):
    query = """
    mutation($input: UpdateProjectV2ItemFieldValueInput!) {
      updateProjectV2ItemFieldValue(input: $input) {
        projectV2Item { id }
      }
    }
    """
    variables = {"input": {"projectId": PROJECT_ID, "itemId": item_id, "fieldId": field_id, "value": value}}
    return run_graphql(query, variables)

def map_option(field_name, option_name):
    option_id = OPTION_IDS.get(field_name, {}).get(option_name)
    if option_id:
        return {"singleSelectOptionId": option_id}
    return None

def parse_date(date_str):
    try:
        date_str = date_str.strip()  # Boşlukları temizle
        if not date_str:
            return None
        dt = parser.parse(date_str)  # Otomatik format çözümü
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"❌ parse_date hatası: '{date_str}' -> {e}")
        return None



# --------------- CSV OKUMA VE ISSUE OLUŞTURMA ----------------
with open("jira_export_all.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader, start=1):
        title = (row.get("Summary") or 'Untitled').strip()
        description = (row.get("Description") or '').strip()
        jira_key = row.get("Issue key", "N/A")
        status = row.get("Status", "Backlog")
        priority = (row.get("Priority") or "Medium").capitalize()
        estimate = row.get("Story Points") or None
        assignee_jira = row.get("Assignee")
        assignee_github = ASSIGNEE_MAP.get(assignee_jira)
        start_date = parse_date(row.get("Start Date") or "")
        end_date = parse_date(row.get("Due date") or "")
        
        print(f"Row {i} - Raw Due Date: {repr(row.get('Due Date'))}")
        print(f"Row {i} - Parsed End Date: {end_date}")
 
        size = row.get("Size")
        milestone = row.get("Milestone")
        development = row.get("Development")

        # Issue body
        body = f"""### 🧩 Jira Bilgileri
**Jira Issue Key:** {jira_key}  
**Status:** {status}  
**Priority:** {priority}  
**Estimate:** {estimate}  

### 📝 Açıklama:
{description or "_Açıklama bulunmuyor_"}"""

        # GitHub Issue oluştur
        data = {"title": title, "body": body}
        if assignee_github:
            data["assignees"] = [assignee_github]

        r = requests.post(f"https://api.github.com/repos/{REPO}/issues", headers=HEADERS, json=data)
        if r.status_code != 201:
            print(f"⚠️ {i}. {title} → Hata ({r.status_code}): {r.text}")
            continue
        
        issue_node_id = r.json()["node_id"]
        print(f"✅ {i}. {title} → Issue başarıyla oluşturuldu.")

        # ProjectV2 item ekle
        item_id = add_item_to_project(issue_node_id)
        if not item_id:
            print(f"⚠️ {i}. {title} → ProjectV2 item eklenemedi.")
            continue
        print(f"    → Project item ID: {item_id}")

        # Alanları güncelle
        if map_option("Status", status):
            update_project_field(item_id, FIELDS["Status"], map_option("Status", status))
        if map_option("Priority", priority):
            update_project_field(item_id, FIELDS["Priority"], map_option("Priority", priority))
        if estimate:
            update_project_field(item_id, FIELDS["Estimate"], {"number": float(estimate)})
        if start_date:
            result = update_project_field(item_id, FIELDS["StartDate"], {"date": start_date})
            print(f"    → StartDate update result: {result}")  # Bu satır response'u gösterecek

        if end_date:
            result = update_project_field(item_id, FIELDS["EndDate"], {"date": end_date})
            print(f"    → EndDate update result: {result}")  # Bu da EndDate response
        if size:
            update_project_field(item_id, FIELDS["Size"], {"number": float(size)})
        if milestone and map_option("Milestone", milestone):
            update_project_field(item_id, FIELDS["Milestone"], map_option("Milestone", milestone))
        if development:
            update_project_field(item_id, FIELDS["Development"], {"text": development})
        if assignee_github:
            # Assignee Project alanı için singleSelectOptionId yerine GitHub username ile atama
            update_project_field(item_id, FIELDS["Assignee"], {"singleSelectOptionId": assignee_github})

        print(f"    → {title} Project alanları güncellendi.\n")
