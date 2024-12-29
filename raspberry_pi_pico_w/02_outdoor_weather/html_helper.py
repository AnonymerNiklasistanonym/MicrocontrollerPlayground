def generate_html(title, body, language="en", css=None, js=None):
    return f"""
    <!DOCTYPE html>
    <html lang="{language}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            {'<style>' + css + '</style>' if css is not None else ''}
        </head>
        <body>{body}</body>
        {'<script>' + js + '</script>' if js is not None else ''}
    </html>
    """


def generate_html_list(elements):
    html = "<ul>"
    for element in elements:
        html += f"<li><p>{element}</p></li>"
    html += "</ul>"
    return html


def generate_html_table(columns, rows):
    html = "<table><tr>"
    for column in columns:
        html += f"<th>{column}</th>"
    html += "</tr>"
    for row in rows:
        html += "<tr>"
        for value in row:
            html += f"<td>{value}</td>"
        html += "</tr>"
    html += "</table>"
    return html


def generate_html_button(title, url):
    return f"<button onclick=\"window.location.href='{url}';\">{title}</button>"
