DROP VIEW IF EXISTS public.v_product_orders_by_month;
CREATE VIEW public.v_product_orders_by_month AS WITH orders_month AS
  (SELECT id AS o_id,
          date_trunc('month'::text, orders.order_datetime) AS order_month
   FROM orders),
            order_month_countid AS
  (SELECT om.order_month,
          COUNT(om.o_id)::numeric AS count_o_id_per_month
   FROM orders_month om
   GROUP BY om.order_month)
SELECT order_month,
       p.product_name,
       count(DISTINCT oi.order_id) AS orders,
       count(DISTINCT oi.order_id) / MAX(o.count_o_id_per_month) AS share_of_orders,
       SUM(oi.quantity) AS total_quantity,
       SUM(p.product_price * (oi.quantity)::double PRECISION) AS total_price
FROM order_items oi
INNER JOIN
  (SELECT om.o_id,
          om.order_month,
          omc.count_o_id_per_month
   FROM orders_month om
   INNER JOIN order_month_countid omc ON omc.order_month = om.order_month
   ORDER BY order_month) o ON o.o_id = oi.order_id
INNER JOIN
  (SELECT id AS p_id,
          product_name,
          product_price
   FROM products) p ON p.p_id = oi.product_id
GROUP BY order_month,
         product_name
ORDER BY order_month,
         product_name;