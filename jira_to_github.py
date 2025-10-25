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
    "Original Estimate": "PVTF_lAHOB0hXU84BFtV0zg3OTbU",
    "Remaining Estimate": "PVTF_lAHOB0hXU84BFtV0zg3OWEY",
    "Time Spent": "PVTF_lAHOB0hXU84BFtV0zg3OaTM",
    "Work Ratio": "PVTF_lAHOB0hXU84BFtV0zg3OaZQ",
    "StartDate": "PVTF_lAHOB0hXU84BFtV0zg296Ds",
    "EndDate": "PVTF_lAHOB0hXU84BFtV0zg296Dw",
    "Size": "PVTF_lAHOB0hXU84BFtV0zg2-DjI",
    "Milestone": "PVTSSF_MILESTONE_ID",
    "Development": "PVTSSF_DEVELOPMENT_ID",
    "Assignee": "PVTSSF_ASSIGNEE_ID",
    "Reporter": "PVTF_lAHOB0hXU84BFtV0zg3NtVs"
}

# Option id eşleşmeleri
OPTION_IDS = {
    "Status": {
        "Başlanmamış": "f75ad846",
        "Devam": "47fc9ee4",
        "Çözülmüş": "98236657"
    },
    "Priority": {
        "Ölümcül": "ac7add12",
        "Kritik": "da944a9c",
        "Majör": "79628723",
        "Düşük": "3e4df051",
        "Minör": "0a877460"
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
    if not option_name:
        return None
    option_name_clean = option_name.strip().lower()  # boşlukları sil, küçük harfe çevir
    for name, oid in OPTION_IDS.get(field_name, {}).items():
        if name.lower() == option_name_clean:
            return {"singleSelectOptionId": oid}
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
    
def seconds_to_duration(sec):
    """
    Saniye cinsinden süreyi Xw Yd Zh formatına çevirir.
    Burada:
      - 1 hafta = 5 gün (iş günü) olarak alınır
      - 1 gün = 8 saat olarak alınır (standart iş günü)
      - Saat ve dakika ayrımı yapılır
    """
    if not sec:
        return None

    sec = int(sec)
    hours_total = sec / 3600  # toplam saat
    weeks = int(hours_total // (8*5))  # 5 iş günü x 8 saat
    hours_total -= weeks * 8 * 5
    days = int(hours_total // 8)
    hours_total -= days * 8
    hours = int(hours_total)
    minutes = int((hours_total - hours) * 60)

    duration_str = ""
    if weeks > 0:
        duration_str += f"{weeks}w "
    if days > 0:
        duration_str += f"{days}d "
    if hours > 0:
        duration_str += f"{hours}h "
    if minutes > 0:
        duration_str += f"{minutes}m"

    return duration_str.strip()



# --------------- CSV OKUMA VE ISSUE OLUŞTURMA ----------------
with open("jira_export_all.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader, start=1):
        title = (row.get("Summary") or 'Untitled').strip()
        description = (row.get("Description") or '').strip()
        jira_key = row.get("Issue key", "N/A")
        project_name = row.get("Project name", "N/A")
        issue_type = row.get("Issue Type", "N/A")
        security_level = row.get("Security Level", "N/A")
        status = row.get("Status", "Backlog")
        priority = (row.get("Priority") or "Medium").capitalize()
        estimate = row.get("Story Points") or None
        original_estimate = row.get("Original Estimate") or None
        remaining_estimate = row.get("Remaining Estimate") or None
        time_spent = row.get("Time Spent") or None
        work_ratio = row.get("Work Ratio") or None
        assignee_jira = row.get("Assignee")
        assignee_github = ASSIGNEE_MAP.get(assignee_jira)
        reporter_jira = row.get("Reporter")
        reporter_github = ASSIGNEE_MAP.get(reporter_jira)
        start_date = parse_date(row.get("Custom field (Start date)") or "")
        end_date = parse_date(row.get("Due Date") or "")
        size = row.get("Size")
        milestone = row.get("Milestone")
        development = row.get("Development")

        # Issue body
        body = f"""{description or "_Açıklama bulunmuyor_"}"""

        # --- SABİT VE CSV LABEL'LARINI TOPLA ---
        csv_labels = []

        with open("jira_export_all.csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)  # İlk satır, sütun isimleri
            # Labels sütunlarının indexlerini bul
            label_indexes = [i for i, h in enumerate(headers) if h == "Labels"]

            for row in reader:
                csv_labels = []
                for idx in label_indexes:
                    val = row[idx].strip()
                    if val:
                        csv_labels.append(val)

        labels = []
        for val in [jira_key, project_name, issue_type, security_level]:
            if val and val.strip():
                labels.append(val)


        for i in csv_labels:
            labels.append(i)
        print(f"\nLabels: {labels}")

        # GitHub Issue oluştur
        data = {
            "title": title,
            "body": body,            
            "labels": labels
        }
        if assignee_github:
            data["assignees"] = [assignee_github]

        r = requests.post(f"https://api.github.com/repos/{REPO}/issues", headers=HEADERS, json=data)

        if r.status_code != 201:
            print(f"⚠️ {i}. {title} → Hata ({r.status_code}): {r.text}")
            continue
        
        issue_node_id = r.json()["node_id"]
        print(f"✅ {title} → Issue başarıyla oluşturuldu.")

        # ProjectV2 item ekle
        item_id = add_item_to_project(issue_node_id)
        if not item_id:
            print(f"⚠️ {i}. {title} → ProjectV2 item eklenemedi.")
            continue

        # Alanları güncelle
        if map_option("Status", status):
            update_project_field(item_id, FIELDS["Status"], map_option("Status", status))
        if map_option("Priority", priority):
            update_project_field(item_id, FIELDS["Priority"], map_option("Priority", priority))
        if estimate:
            update_project_field(item_id, FIELDS["Estimate"], {"number": float(estimate)})
        if original_estimate:
            duration = seconds_to_duration(original_estimate)
            update_project_field(item_id, FIELDS["Original Estimate"], {"text": duration})
        if remaining_estimate:
            duration = seconds_to_duration(remaining_estimate)
            update_project_field(item_id, FIELDS["Remaining Estimate"], {"text":  duration})
        if time_spent:
            duration = seconds_to_duration(time_spent)
            update_project_field(item_id, FIELDS["Time Spent"], {"text":  duration})
        if start_date:
            result = update_project_field(item_id, FIELDS["StartDate"], {"date": start_date})
        if work_ratio:
            update_project_field(item_id, FIELDS["Work Ratio"], {"text": work_ratio})
        if end_date:
            result = update_project_field(item_id, FIELDS["EndDate"], {"date": end_date})
        if size:
            update_project_field(item_id, FIELDS["Size"], {"number": float(size)})
        if milestone and map_option("Milestone", milestone):
            update_project_field(item_id, FIELDS["Milestone"], map_option("Milestone", milestone))
        if development:
            update_project_field(item_id, FIELDS["Development"], {"text": development})
        if assignee_github:
            # Assignee Project alanı için singleSelectOptionId yerine GitHub username ile atama
            update_project_field(item_id, FIELDS["Assignee"], {"singleSelectOptionId": assignee_github})
        if reporter_github:
            update_project_field(item_id, FIELDS["Reporter"], {"text": reporter_github})

        print(f"✅ {title} Issue verileri güncellendi.\n")

#affan