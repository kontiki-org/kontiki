# flake8: noqa


def build_swagger_ui_html(title, spec_url, description=""):
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\">
  <title>{title} - Swagger UI</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui.css\">
  <style> body {{ margin:0; background:#fafafa; }} .topbar {{ display:none; }} </style>
  <meta name=\"description\" content=\"{description}\">
  <script>window.specUrl = '{spec_url}';</script>
  <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
  <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js\"></script>
  <script>
  window.onload = function() {{
    window.ui = SwaggerUIBundle({{
      url: window.specUrl,
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
      layout: 'BaseLayout'
    }});
  }}
  </script>
  </head>
  <body>
    <div id=\"swagger-ui\"></div>
  </body>
</html>
"""
