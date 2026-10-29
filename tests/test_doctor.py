from scripts.doctor import diagnose

def test_doctor_offline_does_not_claim_live_post():
    facts,ready=diagnose(offline=True)
    assert ready
    assert facts["real_facebook_publish_verified"] is False
    assert "server_ready" not in facts
