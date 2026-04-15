from giraffecad.ticket import JointTicket, TimberTicket


class TestTicket:
    def test_horsey_id_auto_increments(self):
        ticket_a = TimberTicket(name="timber_a")
        ticket_b = JointTicket(joint_type="plain_butt")

        assert ticket_b.horsey_id == ticket_a.horsey_id + 1

    def test_horsey_id_does_not_affect_equality_or_hash(self):
        ticket_a = TimberTicket(name="shared_name")
        ticket_b = TimberTicket(name="shared_name")

        assert ticket_a == ticket_b
        assert hash(ticket_a) == hash(ticket_b)
        assert ticket_a.horsey_id != ticket_b.horsey_id