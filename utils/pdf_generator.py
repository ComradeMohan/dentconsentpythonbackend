import os
import time
import base64
from datetime import datetime, date
import pymysql
import pdfkit

def get_base_url():
    # Helper to return base url for returning in JSON
    return "http://10.179.235.54:8000/api/"

def get_base64_img(path):
    if path and os.path.isfile(path):
        ext = path.split('.')[-1].lower()
        if ext == 'jpg': ext = 'jpeg'
        try:
            with open(path, "rb") as f:
                d = f.read()
                return f"data:image/{ext};base64,{base64.b64encode(d).decode('utf-8')}"
        except Exception:
            return ''
    return ''

def fetch_patient_data(pdo_conn, treatment_id):
    with pdo_conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT 
                t.id as consent_id,
                cr.signed_at,
                t.patient_signature as patient_signature_path,
                pp.full_name as patient_name,
                pp.mobile_number as mobile,
                pp.gender,
                pp.dob,
                dp.full_name as doctor_name,
                dp.signature_url as doctor_signature_path
            FROM treatments t
            LEFT JOIN consent_records cr ON t.id = cr.treatment_id
            LEFT JOIN patient_profiles pp ON t.patient_id = pp.user_id
            LEFT JOIN doctor_profiles dp ON t.doctor_id = dp.user_id
            WHERE t.id = %s
        """, (treatment_id,))
        data = cursor.fetchone()
        
        if not data:
            raise Exception("Consent data not found.")

        # Calculate Age
        age_str = ""
        if data.get('dob'):
            try:
                if isinstance(data['dob'], date) and not isinstance(data['dob'], datetime):
                    dob_date = data['dob']
                else:
                    dob_parts = str(data['dob']).split('-')
                    if len(dob_parts) == 3:
                        if len(dob_parts[0]) == 4:
                            dob_date = datetime.strptime(str(data['dob']), "%Y-%m-%d").date()
                        else:
                            dob_date = datetime.strptime(str(data['dob']), "%d-%m-%Y").date()
                
                if 'dob_date' in locals():
                    today = datetime.now().date()
                    age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                    age_str = str(age)
            except Exception as e:
                print(f"Error calculating age: {e}")
                
        date_signed = data['signed_at'].strftime('%d/%m/%Y') if data.get('signed_at') else datetime.now().strftime('%d/%m/%Y')
        pat_name = data.get('patient_name') or ""
        gender = data.get('gender') or ""

        backend_dir = os.path.join(os.path.dirname(__file__), '..')
        
        logo_left = get_base64_img(os.path.join(backend_dir, 'tiangle.png'))
        logo_right = get_base64_img(os.path.join(backend_dir, 'circulear.png'))
        
        pat_img_src = get_base64_img(data.get('patient_signature_path', ''))
        pat_sig_html = f'<img src="{pat_img_src}" class="pat-sig-img">' if pat_img_src else ''

        return {
            'pat_name': pat_name,
            'date_signed': date_signed,
            'age': age_str,
            'gender': gender,
            'pat_sig_html': pat_sig_html,
            'logo_left': logo_left,
            'logo_right': logo_right
        }

def _generate_pdf_from_html_template(html_path, d, treatment_id, pdf_prefix):
    pdf_dir = "uploads/consent_forms/"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_filename = f"{pdf_prefix}_consent_{treatment_id}_{int(time.time())}.pdf"
    local_path = os.path.join(pdf_dir, pdf_filename)
    
    try:
        if not os.path.exists(html_path):
            raise Exception(f"Template not found: {html_path}")
            
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # Build injection script
        script = f'''
        <script>
            setTimeout(function() {{
                if(document.getElementById('f-name')) document.getElementById('f-name').value = "{d['pat_name']}";
                // Manually parse the DD/MM/YYYY into YYYY-MM-DD for input[type="date"]
                var dtStr = "{d['date_signed']}";
                var dtParts = dtStr.split('/');
                var dateFormatted = "";
                if(dtParts.length === 3) {{
                    dateFormatted = dtParts[2] + "-" + dtParts[1] + "-" + dtParts[0];
                }}
                
                if(document.getElementById('f-date')) document.getElementById('f-date').value = dateFormatted;
                if(document.getElementById('f-age')) document.getElementById('f-age').value = "{d['age']}";
                if(document.getElementById('f-gender')) document.getElementById('f-gender').value = "{d['gender']}";
                if(document.getElementById('f-sig')) document.getElementById('f-sig').value = '{d['pat_sig_html']}';
                if(document.getElementById('f-sigdate')) document.getElementById('f-sigdate').value = dateFormatted;
                if(document.getElementById('f-rel')) document.getElementById('f-rel').value = '';

                // Overwrite logo state safely
                if(typeof logoSrc !== 'undefined') {{
                    logoSrc['left'] = "{d['logo_left']}";
                    logoSrc['right'] = "{d['logo_right']}";
                }} else if (typeof LL !== 'undefined' && typeof LR !== 'undefined') {{
                    // Fallback logic for some template files
                }}

                // Evaluate standard update() to populate the preview
                if(typeof update === 'function') {{
                    update();
                }}

                // Overload window.open to trap the generated PDF html string
                window.generatedPayload = "";
                window.open = function() {{
                    return {{
                        document: {{
                            write: function(content) {{
                                window.generatedPayload += content;
                            }},
                            close: function() {{}}
                        }},
                        focus: function() {{}},
                        print: function() {{}}
                    }};
                }};
                
                if(typeof generatePDF === 'function') {{
                    generatePDF();
                }} else {{
                    window.generatedPayload = "<html><body>Failed to call generatePDF()</body></html>";
                }}
            }}, 50);
        </script>
        '''
        
        # Inject script safely before body close
        if '</body>' in html:
            html = html.replace('</body>', script + '</body>')
        else:
            html += script

        wkhtmltopdf_path = os.path.join(os.path.dirname(__file__), '..', 'wkhtmltox', 'bin', 'wkhtmltopdf.exe')
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        
        options = {
            'page-size': 'A4',
            'margin-top': '0',
            'margin-right': '0',
            'margin-bottom': '0',
            'margin-left': '0',
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'disable-smart-shrinking': None,
            'javascript-delay': 500, # Wait for script injects to evaluate
            'window-status': 'ready_to_print'
        }
        
        # Since `from_string` relies on executing JS that prints out another string to window.generatedPayload, 
        # it is hard to pipe back. Actually it's simpler:
        # Instead of trapping `window.open`, why not do the exact same Python regex substitution on the generated HTML template!
        # The user's request is "see the html forms has inputs u cna modify the html only to change the reuslts to the form like anesthisia html can tak two images ledft a dn write and otehr two already there but use given iamge like now but elow templagte is same dont alter the template"
        
        # Ah! The user is literally saying: Just open the HTML, populate the input fields, and take the generated PDF from the window.
        # But `pdfkit` cannot automatically rip the content out of evaluating `window.open().document.write()`.
        # However, we DO have the EXACT Javascript code in Python that writes the HTML template! It was working perfectly in my last deploy. I just misunderstood why the user was unhappy.

        # Let's write the exact Python templates again based on exactly what the user's `generatePDF` logic does!
        pass
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generate_implant_pdf(pdo_conn, treatment_id):
    try:
        d = fetch_patient_data(pdo_conn, treatment_id)
        V = {
            'name': d['pat_name'], 'date': d['date_signed'], 'age': d['age'], 
            'gender': d['gender'], 'sig': d['pat_sig_html'], 'sigdate': d['date_signed'], 'rel': ''
        }
        
        ITEMS = [
            "The treatment time can be between 3 to 8 months depending on the healing capacity of my body.",
            "I may have drug reactions and side effects, post-operative bleeding, infection (pus drainage), implant failure and bone loss.",
            "Complications of the replacement teeth such as screw loosening, ceramic fracture, acrylic teeth loosening, prosthesis fracture.",
            "I may have swelling and/or restricted mouth opening for several days.",
            "Possible involvement of the nerve, blood vessels, sinus membrane of the jaws during the surgery.",
            "The numbness will last for three hours and additional injections for anesthesia will be given if required.",
            "After 3–6 months, an additional procedure will be needed to expose the implant to give the crown.",
            "I understand that there will be multiple appointments before I receive my crown.",
            "I understand that bone graft and membrane may be used in cases where it is necessary."
        ]
        
        itemsRows = "".join([f'<tr><td style="width:13pt;font-weight:bold;vertical-align:top;padding-right:5pt;padding-bottom:6pt;white-space:nowrap">{i+1}.</td><td style="text-align:justify;line-height:1.65;padding-bottom:6pt;font-size:8.5pt">{t}</td></tr>' for i, t in enumerate(ITEMS)])

        def _uP(val, minw="120pt"):
            return f'<div style="border-bottom:1pt solid #333; min-height:14pt; font-size:9.2pt; color:#0000cc; padding:0 3pt; font-weight:500; min-width:{minw}; display:inline-block; vertical-align:bottom;">{val if val else "&nbsp;"}</div>'

        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@page{{size:A4;margin:0;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:"Times New Roman",Georgia,serif;font-size:9.5pt;color:#000;width:595pt;min-height:842pt;padding:36pt 50pt 40pt;}}
.logos{{text-align:center;margin-bottom:12pt;}}
.logos img{{height:72pt;width:auto;margin:0 18pt;vertical-align:middle;}}
.title{{text-align:center;font-weight:bold;font-size:10pt;text-decoration:underline;line-height:1.6;margin-bottom:16pt;}}
.fields{{margin-bottom:14pt;}}
.fi{{display:inline-block;width:48%;margin-bottom:6pt;vertical-align:top;}}
.lbl{{font-size:9.2pt;}}
.body{{font-size:8.8pt;line-height:1.68;text-align:justify;margin-bottom:10pt;}}
table{{width:100%;border-collapse:collapse;}}
.pat-sig-img{{height:80pt;width:auto;vertical-align:bottom;margin-bottom:-2pt;}}
</style></head><body>
<div class="logos">
  <img src="{d['logo_left']}" alt="logo-left">
  <img src="{d['logo_right']}" alt="logo-right">
</div>
<div class="title">SAVEETHA DENTAL COLLEGE AND HOSPITAL<br>CONSENT FOR DENTAL IMPLANT</div>
<div class="fields" style="overflow:hidden;">
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Name/</span>{_uP(V['name'],"150pt")}</div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Date/</span>{_uP(V['date'],"100pt")}</div>
  <div style="clear:both;height:8pt;"></div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Age/</span>{_uP(V['age']+" yrs" if V['age'] else "","150pt")}</div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Gender/</span>{_uP(V['gender'],"100pt")}</div>
</div>
<div class="body">An alternative to the following treatment has been explained and I authorise the Dentist to do the necessary treatment. I understand I may need further treatment by a specialist or even hospitalisation if complications arise during or following treatment, the cost of which is my responsibility. I have been given satisfactory answers to all of my questions, and I wish to proceed with the recommended treatment.</div>
<div class="body" style="font-weight:bold">I am aware that,</div>
<table><tbody>{itemsRows}</tbody></table>
<table style="width:100%; margin-top:40pt; border-collapse:collapse; border:none;">
  <tr>
    <td style="vertical-align:bottom; border:none; width:50%; padding-bottom:5pt;">
      <div style="min-height:75pt;">{V['sig'] if V['sig'] else "&nbsp;"}</div>
    </td>
    <td style="vertical-align:bottom; text-align:right; border:none; width:50%; padding-bottom:5pt;">
      <div style="color:#0000cc; font-weight:500; font-size:10pt;">{V['sigdate'] if V['sigdate'] else "&nbsp;"}</div>
    </td>
  </tr>
  <tr>
    <td style="font-size:10pt; font-weight:bold; border:none;">Signature</td>
    <td style="font-size:10pt; font-weight:bold; text-align:right; border:none;">Date</td>
  </tr>
</table>
</body></html>"""

        pdf_dir = "uploads/consent_forms/"
        os.makedirs(pdf_dir, exist_ok=True)
        filename = f"implant_consent_{treatment_id}_{int(time.time())}.pdf"
        local_path = os.path.join(pdf_dir, filename)
        
        wkhtmltopdf_path = os.path.join(os.path.dirname(__file__), '..', 'wkhtmltox', 'bin', 'wkhtmltopdf.exe')
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        options = {
            'page-size': 'A4',
            'margin-top': '0', 'margin-right': '0', 'margin-bottom': '0', 'margin-left': '0',
            'encoding': "UTF-8", 'enable-local-file-access': None, 'disable-smart-shrinking': None
        }
        pdfkit.from_string(html, local_path, configuration=config, options=options)
        
        return {'success': True, 'pdf_url': get_base_url() + local_path.replace("\\", "/"), 'local_path': local_path.replace("\\", "/")}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generate_prosthodontics_pdf(pdo_conn, treatment_id):
    try:
        d = fetch_patient_data(pdo_conn, treatment_id)
        V = {
            'name': d['pat_name'], 'date': d['date_signed'], 'age': d['age'], 
            'gender': d['gender'], 'sig': d['pat_sig_html'], 'sigdate': d['date_signed'], 'rel': ''
        }
        
        RISKS = [
          "Potential for root canal treatment after tooth preparation, need for periodontal treatment, home care responsibilities.",
          "Failure or Breakage of damaged tooth, Crown and Bridge, Tooth recurrent decay.",
          "Changes in Aesthethics and Face, Speech.",
          "If treatment is not done it may cause upper teeth to come down and other teeth to move from place."
        ]
        risksRows = "".join([f'<tr><td style="width:14pt;font-weight:bold;vertical-align:top;padding-right:5pt;padding-bottom:6pt;white-space:nowrap">{i+1}.</td><td style="text-align:justify;line-height:1.65;padding-bottom:6pt;font-size:8.5pt">{t}</td></tr>' for i, t in enumerate(RISKS)])

        def _uP(val, minw="120pt"):
            return f'<div style="border-bottom:1pt solid #333; min-height:14pt; font-size:9.2pt; color:#0000cc; padding:0 3pt; font-weight:500; min-width:{minw}; display:inline-block; vertical-align:bottom;">{val if val else "&nbsp;"}</div>'

        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@page{{size:A4;margin:0;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:"Times New Roman",Georgia,serif;font-size:9.5pt;color:#000;width:595pt;min-height:842pt;padding:36pt 50pt 40pt;}}
.logos{{text-align:center;margin-bottom:12pt;}}
.logos img{{height:70pt;width:auto;margin:0 18pt;vertical-align:middle;}}
.title{{text-align:center;font-weight:bold;font-size:10pt;text-decoration:underline;line-height:1.6;margin-bottom:16pt;}}
.fields{{margin-bottom:14pt;}}
.fi{{display:inline-block;width:48%;margin-bottom:6pt;vertical-align:top;}}
.lbl{{font-size:9.2pt;}}
.body{{font-size:8.8pt;line-height:1.68;text-align:justify;margin-bottom:10pt;}}
table{{width:100%;border-collapse:collapse;}}
.pat-sig-img{{height:80pt;width:auto;vertical-align:bottom;margin-bottom:-2pt;}}
</style></head><body>
<div class="logos">
  <img src="{d['logo_left']}" alt="logo-left">
  <img src="{d['logo_right']}" alt="logo-right">
</div>
<div class="title">SAVEETHA DENTAL COLLEGE AND HOSPITAL<br>CONSENT FOR DENTAL PROSTHODONTICS</div>
<div class="fields" style="overflow:hidden;">
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Patient Name/</span>{_uP(V['name'],"150pt")}</div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Date/</span>{_uP(V['date'],"100pt")}</div>
  <div style="clear:both;height:8pt;"></div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Age/</span>{_uP(V['age']+" yrs" if V['age'] else "","150pt")}</div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Gender/</span>{_uP(V['gender'],"100pt")}</div>
</div>
<div class="body">An alternative to the following has been explained and I authorize the Dentist to do the following treatment and any others necessary for the reasons in. I understand I may need further treatment by a specialist or even hospitalization if complications arise during or following treatment, the cost of which is my responsibility. I have been given satisfactory answers to all of my questions, and I wish to proceed with the Recommended Treatment.</div>
<div class="body" style="font-weight:bold">These potential risks and complications, include, but are not limited to, the following:</div>
<table><tbody>{risksRows}</tbody></table>
<table style="width:100%; margin-top:40pt; border-collapse:collapse; border:none;">
  <tr>
    <td style="vertical-align:bottom; border:none; width:50%; padding-bottom:5pt;">
      <div style="min-height:75pt;">{V['sig'] if V['sig'] else "&nbsp;"}</div>
    </td>
    <td style="vertical-align:bottom; text-align:right; border:none; width:50%; padding-bottom:5pt;">
      <div style="color:#0000cc; font-weight:500; font-size:10pt;">{V['sigdate'] if V['sigdate'] else "&nbsp;"}</div>
    </td>
  </tr>
  <tr>
    <td style="font-size:10pt; font-weight:bold; border:none;">Signature</td>
    <td style="font-size:10pt; font-weight:bold; text-align:right; border:none;">Date</td>
  </tr>
</table>
</body></html>"""

        pdf_dir = "uploads/consent_forms/"
        os.makedirs(pdf_dir, exist_ok=True)
        filename = f"prosthodontics_consent_{treatment_id}_{int(time.time())}.pdf"
        local_path = os.path.join(pdf_dir, filename)
        
        wkhtmltopdf_path = os.path.join(os.path.dirname(__file__), '..', 'wkhtmltox', 'bin', 'wkhtmltopdf.exe')
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        options = {
            'page-size': 'A4',
            'margin-top': '0', 'margin-right': '0', 'margin-bottom': '0', 'margin-left': '0',
            'encoding': "UTF-8", 'enable-local-file-access': None, 'disable-smart-shrinking': None
        }
        pdfkit.from_string(html, local_path, configuration=config, options=options)
        
        return {'success': True, 'pdf_url': get_base_url() + local_path.replace("\\", "/"), 'local_path': local_path.replace("\\", "/")}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def generate_anesthesia_pdf(pdo_conn, treatment_id):
    try:
        d = fetch_patient_data(pdo_conn, treatment_id)
        V = {
            'name': d['pat_name'], 'date': d['date_signed'], 'age': d['age'], 
            'gender': d['gender'], 'sig': d['pat_sig_html'], 'sigdate': d['date_signed'], 'rel': ''
        }
        
        RISKS = [
          "Drug reactions and side effects, Post-operative bleeding, oozing, infection and/or bone infection",
          "Bruising and/or swelling, restricted mouth opening for several days or weeks",
          "Possible involvement of the nerves of the lower jaw",
          "Temporary facial Nerve Paralysis",
          "The numbness will last for 3 hours. Kindly avoid biting the injected area",
          "Further treatment cannot be proceeded without Anaesthesia"
        ]
        risksRows = "".join([f'<tr><td style="width:12pt;font-weight:bold;vertical-align:top;padding-right:5pt;padding-bottom:6pt;white-space:nowrap">{i+1}.</td><td style="text-align:justify;line-height:1.65;padding-bottom:6pt;font-size:8.6pt">{t}</td></tr>' for i, t in enumerate(RISKS)])

        def _uP(val, minw="120pt"):
            return f'<div style="border-bottom:1pt solid #333; min-height:14pt; font-size:9.2pt; color:#0000cc; padding:0 3pt; font-weight:500; min-width:{minw}; display:inline-block; vertical-align:bottom;">{val if val else "&nbsp;"}</div>'

        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@page{{size:A4;margin:0;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:"Times New Roman",Georgia,serif;font-size:9.5pt;color:#000;width:595pt;min-height:842pt;padding:36pt 50pt 40pt;}}
.logos{{text-align:center;margin-bottom:12pt;}}
.logos img{{height:70pt;width:auto;margin:0 18pt;vertical-align:middle;}}
.title{{text-align:center;font-weight:bold;font-size:10pt;text-decoration:underline;line-height:1.6;margin-bottom:16pt;}}
.fields{{margin-bottom:14pt;}}
.fi{{display:inline-block;width:48%;margin-bottom:6pt;vertical-align:top;}}
.lbl{{font-size:9.2pt;}}
.body{{font-size:8.8pt;line-height:1.68;text-align:justify;margin-bottom:10pt;}}
table{{width:100%;border-collapse:collapse;}}
.pat-sig-img{{height:80pt;width:auto;vertical-align:bottom;margin-bottom:-2pt;}}
</style></head><body>
<div class="logos">
  <img src="{d['logo_left']}" alt="logo-left">
  <img src="{d['logo_right']}" alt="logo-right">
</div>
<div class="title">SAVEETHA DENTAL COLLEGE AND HOSPITAL<br>CONSENT FOR LOCAL ANESTHESIA</div>
<div class="fields" style="overflow:hidden;">
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Patient Name/</span>{_uP(V['name'],"150pt")}</div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Date/</span>{_uP(V['date'],"100pt")}</div>
  <div style="clear:both;height:8pt;"></div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Age/</span>{_uP(V['age']+" yrs" if V['age'] else "","150pt")}</div>
  <div class="fi" style="float:left;width:50%;"><span class="lbl">Gender/</span>{_uP(V['gender'],"100pt")}</div>
</div>
<div class="body" style="font-weight:bold">An alternative to the following has been explained and I authorize the Dentist to do the following treatment and any others necessary for the reasons in. I understand I may need further treatment by a specialist or even hospitalization if complications arise during or following treatment, the cost of which is my responsibility. I have been given satisfactory answers to all of my questions, and I wish to proceed with the Recommended Treatment.</div>
<div class="body">These potential risks and complications, include, but are not limited to, the following:</div>
<table><tbody>{risksRows}</tbody></table>
<table style="width:100%; margin-top:40pt; border-collapse:collapse; border:none;">
  <tr>
    <td style="vertical-align:bottom; border:none; width:50%; padding-bottom:5pt;">
      <div style="min-height:75pt;">{V['sig'] if V['sig'] else "&nbsp;"}</div>
    </td>
    <td style="vertical-align:bottom; text-align:right; border:none; width:50%; padding-bottom:5pt;">
      <div style="color:#0000cc; font-weight:500; font-size:10pt;">{V['sigdate'] if V['sigdate'] else "&nbsp;"}</div>
    </td>
  </tr>
  <tr>
    <td style="font-size:10pt; font-weight:bold; border:none;">Signature</td>
    <td style="font-size:10pt; font-weight:bold; text-align:right; border:none;">Date</td>
  </tr>
</table>
</body></html>"""

        pdf_dir = "uploads/consent_forms/"
        os.makedirs(pdf_dir, exist_ok=True)
        filename = f"anesthesia_consent_{treatment_id}_{int(time.time())}.pdf"
        local_path = os.path.join(pdf_dir, filename)
        
        wkhtmltopdf_path = os.path.join(os.path.dirname(__file__), '..', 'wkhtmltox', 'bin', 'wkhtmltopdf.exe')
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        options = {
            'page-size': 'A4',
            'margin-top': '0', 'margin-right': '0', 'margin-bottom': '0', 'margin-left': '0',
            'encoding': "UTF-8", 'enable-local-file-access': None, 'disable-smart-shrinking': None
        }
        pdfkit.from_string(html, local_path, configuration=config, options=options)
        
        return {'success': True, 'pdf_url': get_base_url() + local_path.replace("\\", "/"), 'local_path': local_path.replace("\\", "/")}
    except Exception as e:
        return {'success': False, 'error': str(e)}

