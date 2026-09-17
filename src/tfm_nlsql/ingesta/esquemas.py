"""Esquema estructural de los CSV de Olist (nombres de origen, D-36).

La validación de Landing es de cabecera y de parseo CSV, no de tipos de
negocio: eso es Silver.
"""

from __future__ import annotations

CSV_OBLIGATORIOS = (
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
)

CSV_FUNNEL = (
    "olist_marketing_qualified_leads_dataset.csv",
    "olist_closed_deals_dataset.csv",
)

ESQUEMAS: dict[str, tuple[str, ...]] = {
    "olist_orders_dataset.csv": (
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ),
    "olist_order_items_dataset.csv": (
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ),
    "olist_order_payments_dataset.csv": (
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ),
    "olist_order_reviews_dataset.csv": (
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    ),
    "olist_customers_dataset.csv": (
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ),
    "olist_products_dataset.csv": (
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ),
    "olist_sellers_dataset.csv": (
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ),
    "olist_marketing_qualified_leads_dataset.csv": (
        "mql_id",
        "first_contact_date",
        "landing_page_id",
        "origin",
    ),
    "olist_closed_deals_dataset.csv": (
        "mql_id",
        "seller_id",
        "sdr_id",
        "sr_id",
        "won_date",
        "business_segment",
        "lead_type",
        "lead_behaviour_profile",
        "has_company",
        "has_gtin",
        "average_stock",
        "business_type",
        "declared_product_catalog_size",
        "declared_monthly_revenue",
    ),
}
