import pdfkit, os, base64

def get_base64_img(path):
    if path and os.path.isfile(path):
        ext = path.split('.')[-1].lower()
        if ext == 'jpg': ext = 'jpeg'
        try:
            with open(path, 'rb') as f:
                d = f.read()
                return f'data:image/{ext};base64,{base64.b64encode(d).decode("utf-8")}'
        except Exception:
            pass
    return ''

wkhtmltopdf_path = os.path.join(r'C:\xampp\htdocs\dentconsent\python_backend', 'wkhtmltox', 'bin', 'wkhtmltopdf.exe')
config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

with open(os.path.join(r'C:\xampp\htdocs\dentconsent\python_backend', 'saveetha_consent_english.html'), 'r', encoding='utf-8') as f:
    html = f.read()

logo_l = get_base64_img(r'C:\xampp\htdocs\dentconsent\python_backend\tiangle.png')
logo_r = get_base64_img(r'C:\xampp\htdocs\dentconsent\python_backend\circulear.png')

script = f"""
<script>
  setTimeout(function() {{
      if(document.getElementById('f-name')) document.getElementById('f-name').value = 'Test Patient';
      if(document.getElementById('f-date')) document.getElementById('f-date').value = '2023-10-10';
      if(document.getElementById('f-age')) document.getElementById('f-age').value = '30';
      if(document.getElementById('f-gender')) document.getElementById('f-gender').value = 'Male';
      if(document.getElementById('f-sig')) document.getElementById('f-sig').value = '<img src="{logo_l}" style="max-height: 40px; margin-bottom:-10px;">';
      if(document.getElementById('f-sigdate')) document.getElementById('f-sigdate').value = '2023-10-10';
      if(document.getElementById('f-rel')) document.getElementById('f-rel').value = 'Father';
      
      if(typeof logoSrc !== 'undefined') {{
          logoSrc['left'] = "{logo_l}";
          logoSrc['right'] = "{logo_r}";
      }}
      
      window.open = function() {{
          return {{
              document: {{
                  write: function(content) {{
                      document.open();
                      document.write(content);
                  }},
                  close: function() {{}}
              }},
              focus: function() {{}},
              print: function() {{}}
          }};
      }};
      generatePDF();
  }}, 100);
</script>
"""

html_modified = html.replace('</body>', script + '</body>')

options = {
    'page-size': 'A4',
    'margin-top': '0', 'margin-right': '0', 'margin-bottom': '0', 'margin-left': '0',
    'encoding': 'UTF-8',
    'enable-local-file-access': None,
    'disable-smart-shrinking': None,
    'javascript-delay': 1000
}

pdfkit.from_string(html_modified, 'test_js_eval_anesthesia.pdf', configuration=config, options=options)
print("done")
