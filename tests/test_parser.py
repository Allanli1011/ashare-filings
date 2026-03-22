from src.parser.html_extractor import extract_text_from_html
from src.parser.pdf_extractor import extract_text_from_pdf_bytes

def test_extract_text_from_html():
    html = """
    <html>
        <head>
            <title>Test</title>
            <script>alert('not text');</script>
            <style>.body { color: red; }</style>
        </head>
        <body>
            <div class="detail-body">
                <p>Important announcement text.</p>
                <p>Second line.</p>
            </div>
            <footer>Not this part</footer>
        </body>
    </html>
    """
    text = extract_text_from_html(html)
    assert "Important announcement text." in text
    assert "Second line." in text
    assert "not text" not in text
    assert "color: red" not in text
    assert "Not this part" not in text

def test_extract_html_no_content_div():
    html = "<html><body><p>Just some text</p></body></html>"
    text = extract_text_from_html(html)
    assert "Just some text" in text

def test_extract_text_from_pdf_bytes_invalid(caplog):
    # Invalid PDF bytes should be caught and return empty string
    invalid_bytes = b"not a real pdf"
    text = extract_text_from_pdf_bytes(invalid_bytes)
    assert text == ""
    assert "PDF 文本提取失败" in caplog.text

def test_extract_text_from_empty_html():
    assert extract_text_from_html("") == ""
