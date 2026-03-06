import os
import sys

# Add parent dir to path so we can import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from xhtml2pdf import pisa

# Mock patient data
d = {
    'pat_name': 'John Doe',
    'date_signed': '15/03/2026',
    'age': '25 yrs',
    'gender': 'Male',
    'logo_left': '',
    'logo_right': '',
    'pat_sig_html': '<span>Mock Signature</span>'
}

html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Implant Consent</title>
<style>
@page {{ size: a4 portrait; margin: 30pt 40pt; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: "Times New Roman", Georgia, serif; font-size: 10pt; color: #000; line-height: 1.5; border: 1.5pt solid #000; padding: 30pt; }}
.logos {{ text-align: center; margin-bottom: 10pt; }}
.logos img {{ height: 72pt; width: auto; display: inline-block; margin: 0 17pt; }}
.title {{ text-align: center; font-size: 9.8pt; line-height: 1.6; margin-bottom: 13pt; }}
.fields {{ width: 100%; margin-bottom: 12pt; border-collapse: collapse; }}
.fields td {{ padding-bottom: 5pt; font-size: 9.2pt; }}
.uP {{ display: inline-block; border-bottom: 1pt solid #333; color: #0000cc; font-weight: 500; padding: 0 3pt; font-size: 9.2pt; vertical-align: bottom; }}
.body {{ font-size: 8.7pt; line-height: 1.68; text-align: justify; margin-bottom: 9pt; }}
.aware {{ font-size: 9pt; font-weight: bold; margin-bottom: 6pt; }}
table.risks {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
.sr {{ width: 100%; margin-top: 22pt; border-collapse: collapse; }}
</style></head><body>
<div class="logos">
    <img src="{d['logo_left']}" alt="">
    <img src="{d['logo_right']}" alt="">
</div>
<div class="title">
    <strong>Saveetha Dental College &amp; Hospital</strong><br>
    <strong>Consent For Dental Implant</strong>
</div>
<table class="fields">
    <tr>
        <td style="width:50%">Name: <span class="uP" style="min-width:140pt">{d['pat_name']}</span></td>
        <td style="width:50%">Date: <span class="uP" style="min-width:100pt">{d['date_signed']}</span></td>
    </tr>
    <tr>
        <td>Age: <span class="uP" style="min-width:140pt">{d['age']}</span></td>
        <td>Gender: <span class="uP" style="min-width:100pt">{d['gender']}</span></td>
    </tr>
</table>
<div class="body">An alternative to the following treatment has been explained...</div>
</body></html>"""

with open("test_implant.pdf", "w+b") as result_file:
    pisa_status = pisa.CreatePDF(html, dest=result_file)
print("Error:", pisa_status.err)
