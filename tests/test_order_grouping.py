from order_error_capture import OrderFailure, OrderStage, grouping_fingerprint


def test_grouping_tracks_failure_kind_instead_of_individual_order() -> None:
    first_order = OrderFailure(
        event_id="evt-101",
        order_id="order-101",
        stage=OrderStage.CHECKOUT,
        operation="authorize_payment",
        exception_type="PaymentDeclined",
        message="issuer declined authorization",
    )
    second_order = OrderFailure(
        event_id="evt-202",
        order_id="order-202",
        stage=OrderStage.CHECKOUT,
        operation="authorize_payment",
        exception_type="PaymentDeclined",
        message="authorization was declined",
    )
    receipt_failure = OrderFailure(
        event_id="evt-303",
        order_id="order-101",
        stage=OrderStage.RECEIPT,
        operation="send_receipt",
        exception_type="DeliveryError",
        message="receipt delivery rejected",
    )

    assert grouping_fingerprint(first_order) == grouping_fingerprint(second_order)
    assert grouping_fingerprint(first_order) != grouping_fingerprint(receipt_failure)
