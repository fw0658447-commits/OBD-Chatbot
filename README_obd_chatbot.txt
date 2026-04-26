OBD System Review Assistant – Startanleitung

1. Python installieren (falls noch nicht vorhanden)
2. Im Terminal in den Ordner mit der Datei wechseln
3. Abhängigkeit installieren:
   pip install -r requirements_obd_chatbot.txt
4. App starten:
   streamlit run obd_chatbot_app.py
5. Im Browser die angezeigte lokale Adresse öffnen

Enthaltene Themen:
- OBD EU7
- Wirkkettenanalyse
- OBM
- OBF(C)M
- Anti-Tampering
- Felddatenanalyse
- HIL / virtuelle Validierung

Hinweis:
Diese erste Version ist bewusst einfach gehalten und nutzt feste Fachlogik.
Im nächsten Ausbau kann man ergänzen:
- Upload von PDF/Excel/DOCX
- Antwortlogik je Rolle (Management / Engineering / Zertifizierung)
- Maßnahmenlisten und Ampelstatus
- Aufwandsschätzung / PM-Kalkulation
- Suche in eigenen Dokumenten
