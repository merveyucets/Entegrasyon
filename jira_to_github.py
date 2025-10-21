import csv
import requests
import os
from datetime import datetime
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
    "Estimate": "PVTSSF_ESTIMATE_ID",      # kendi field id’si ile değiştir
    "StartDate": "PVTSSF_STARTDATE_ID",
    "EndDate": "PVTSSF_ENDDATE_ID",
    "Size": "PVTSSF_SIZE_ID",
    "Milestone": "PVTSSF_MILESTONE_ID",
    "Development": "PVTSSF_DEVELOPMENT_ID",
    "Assignee": "PVTSSF_ASSIGNEE_ID"
}

# Option id eşleşmeleri
OPTION_IDS = {
    "Status": {
        "Başlanmamış": "f75ad846",
        "Devam": "47fc9ee4",
        "Çözülmüş": "98236657"
    },
    "Priority": {
        "Lowest": "79628723",
        "Low": "0a877460",
        "Medium": "da944a9c",
        "Highest": "ac7add12"
    }
}

# Jira kullanıcı adlarını GitHub kullanıcı adlarına eşleme
ASSIGNEE_MAP = {
    "Affan B.": "affanbaykar",
    "myucetass99": "merveyucets"
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
        item {
          id
        }
      }
    }
    """
    variables = {"projectId": PROJECT_ID, "contentId": issue_node_id}
    result = run_graphql(query, variables)
    print("GraphQL addProjectV2ItemById result:", result)  # <- burayı ekle
    if result:
        return result["data"]["addProjectV2ItemById"]["item"]["id"]
    return None

def update_project_field(item_id, field_id, value):
    query = """
    mutation($input: UpdateProjectV2ItemFieldValueInput!) {
      updateProjectV2ItemFieldValue(input: $input) {
        projectV2Item {
          id
        }
      }
    }
    """
    variables = {
        "input": {
            "projectId": PROJECT_ID,
            "itemId": item_id,
            "fieldId": field_id,
            "value": value
        }
    }
    return run_graphql(query, variables)

def map_option(field_name, option_name):
    if not option_name:
        return None
    option_name_clean = option_name.strip().lower()  # boşlukları sil, küçük harfe çevir
    for name, oid in OPTION_IDS.get(field_name, {}).items():
        if name.lower() == option_name_clean:
            return {"singleSelectOptionId": oid}
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
        
        # Issue body
        body = f"""### 🧩 Jira Bilgileri
**Jira Issue Key:** {jira_key}  
**Status:** {status}  
**Priority:** {priority}  
**Estimate:** {estimate}  

### 📝 Açıklama:
{description or "_Açıklama bulunmuyor_"}"""

        # GitHub Issue oluştur
        data = {
            "title": title,
            "body": body,             # body hâlâ tüm açıklamayı içeriyor
            "labels": [jira_key]      # sadece Jira issue key’i label olarak eklendi
        }
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
        # Status
        status_value = map_option("Status", status)
        if status_value:
            update_project_field(item_id, FIELDS["Status"], status_value)
        # Priority
        priority_value = map_option("Priority", priority)
        if priority_value:
            update_project_field(item_id, FIELDS["Priority"], priority_value)
        # Estimate (number)
        if estimate:
            update_project_field(item_id, FIELDS["Estimate"], {"number": float(estimate)})
        # Assignee
        if assignee_github:
            update_project_field(item_id, FIELDS["Assignee"], {"singleSelectOptionId": assignee_github})
        # Not: diğer alanlar (StartDate, EndDate, Size, Milestone, Development) aynı mantıkla eklenebilir
        print(f"    → {title} Project alanları güncellendi.\n")
