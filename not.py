

REPO = "merveyucets/Entegrasyon"  # Kendi repo adın
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


with open("jira_export_all.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print({
            "title": row["Summary"],
            "status": row["Status"],
            "priority": row["Priority"],
            "reporter": row["Reporter"]
        })
        
# 💾 CSV'yi oku
with open('jira_export_all.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for i, row in enumerate(reader, start=1):
        title = (row.get('Summary') or 'Untitled').strip()
        jira_key = row.get('Issue key', 'N/A')
        status = row.get('Status', 'N/A')
        priority = (row.get('Priority') or 'Medium').strip().capitalize()
        estimate = (row.get('Story Points') or 'N/A')
        
        # GitHub'da Priority ve Estimate etiketleri oluştur
        labels = ["from-jira"]

        if priority in ["High", "Medium", "Low"]:
            labels.append(f"Priority: {priority}")
        if estimate != "N/A":
            labels.append(f"Estimate: {estimate}")
        
        description = (row.get('Description') or '').strip()

        body = f"""### 🧩 Jira Bilgileri
**Jira Issue Key:** {jira_key}  
**Durum:** {status}  
**Öncelik:** {priority}  
**Tahmini Süre:** {estimate}  
---

### 📝 Açıklama:
{description or '_Açıklama bulunmuyor_'}
"""

        data = {
            "title": title,
            "body": body,
            "labels": labels
        }

        r = requests.post(
            f"https://api.github.com/repos/{REPO}/issues",
            headers=HEADERS,
            json=data
        )

        if r.status_code == 201:
            print(f"✅ {i}. {title} → başarıyla eklendi.")
        else:
            print(f"⚠️ {i}. {title} → Hata ({r.status_code}): {r.text}")