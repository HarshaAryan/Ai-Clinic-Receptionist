from routers.whatsapp import _extract_payload, _extract_message


def test_extract_message():
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": "123", "text": {"body": "hi"}}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    value = _extract_payload(payload)
    msg = _extract_message(value)
    assert msg["from"] == "123"
    assert msg["text"] == "hi"
