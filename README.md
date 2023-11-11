# Data Engineering Case Study with SQL Optimization and Python Data Integration - Installing, Running, and Report

## Installing Instructions

+ Install the necessary initial packages and update the package manager:
```bash
sudo apt update -y
sudo apt install gnupg2 wget vim -y
```

+ Install the packages for PostgreSQL and start/enable the PostgreSQL
```bash
sudo apt-get -y install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

+ Check if PostgreSQL has been successfully set up 
```bash
systemctl status postgresql # The status should be "active"
psql --version # This should give the version of PostgreSQL
sudo -u postgres psql -c "SELECT version();" # This should also give the version of PostgreSQL
```

+ Edit the `postgresql.conf` file:
  - Execute this command: `sudo vim /etc/postgresql/14/main/postgresql.conf`
  - Change the line `#listen_addresses = 'localhost'` to `listen_addresses = '*'`

+ Add a new line to the `pg_hba.conf` file by executing the following command:
```bash
sudo sed -i '/^host/s/ident/md5/' /etc/postgresql/14/main/pg_hba.conf
```

+ Now, edit IPv4 local connections in `pg_hba.conf`:
  - Execute this command: `sudo vim /etc/postgresql/14/main/pg_hba.conf`
  - Edit the lines in the following way:
  ```
  # IPv4 local connections:
  host    all             all             127.0.0.1/32        scram-sha-256
  host    all             all             0.0.0.0/0           scram-sha-256
  ```

+ Restart PostgreSQL and allow the fire wall to accept connections to `5432/tcp`:
```bash
sudo systemctl restart postgresql
sudo ufw allow 5432/tcp
```

+ Set the password as `Str0ngP@ssw0rd` of PostgreSQL for connections:
```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'Str0ngP@ssw0rd';"
```

+ Build the python virtual environment with all the packages by executing the following command:
```bash
./build.sh
```


## Running Instructions

+ Load the original database by executing the following command in command line:

```bash
psql -d postgres -h localhost -U postgres -f sql/db_backup.sql
```

**Note:** Provide `Str0ngP@ssw0rd` as password.

+ Optimize `public.v_product_orders_by_month` with the sql file `optimize_view.sql` by executing the following command in command line:

```bash
psql -d postgres -h localhost -U postgres -f sql/optimize_view.sql
```

**Note:** Provide `Str0ngP@ssw0rd` as password.

+ Now, the view `public.v_product_orders_by_month` has been optimized.


+ Activate the virtual environment by executing the following command:
```bash
source ./venv/bin/activate
```

+ In order to enrich the company domains with industries, execute the following command:
```bash
python3 company_enrichment.py --cached
```

**Important Note:** Since the Apollo.io account is not a premium account, the script doesn't let you to send more than 100 requests per hour. Also, it prevents you to send more than 20 requests per minute. If you want to fetch the result without the `--cached` industries, please use a *premium* api key! In this case, simply execute `bash
python3 company_enrichment.py`.

+ Dump the new database to `sql/new_db_backup.sql` by executing the following command in command line:

```bash
pg_dump -C -h localhost -U postgres -d postgres -f sql/new_db_backup.sql
```

**Note:** Provide `Str0ngP@ssw0rd` as password.

+ You can now check `sql/new_db_backup.sql` to see the final version of the database.


## Report


+ **The Steps taken to Optimize the Performance of the View `public.v_product_orders_by_month`:**
  - Unnecessary joins have been removed and the number of joins reduced from 5 to 3.
  - `Total Price` and `Total Quantity` calculations are done at the same time at the end and only once.
  - LEFT JOINS converted to INNER JOINS since INNER JOINS are more high performant.
  - Avoided multiple joins on the month of order_month. 
  - Unnecessary column selections are removed (e.g customer_id).
  - In order to speed up the new view, the following SQL queries have been executed in the database to add further indexes and constraints:
    
    ```sql
      ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_id_pkey;
      ALTER TABLE ONLY public.orders ADD CONSTRAINT orders_id_pkey PRIMARY KEY (id); --- Added Primary Key for: `public.orders.id`

      ALTER TABLE public.order_items DROP CONSTRAINT IF EXISTS order_items_id_pkey;
      ALTER TABLE ONLY public.order_items ADD CONSTRAINT order_items_id_pkey PRIMARY KEY (id); --- Added Primary Key for: `public.order_items.id`

      DROP INDEX IF EXISTS fk_index_product_id;
      CREATE INDEX fk_index_product_id ON public.order_items (product_id); -- Added indexes to the column: `public.order_items.product_id`
    ```

+ **Performance Comparison of 10 Executions (in `ms`):**
  - **Original View Query (Mean: `487.04`):** `495.654, 483.300, 484.654, 487.330, 497.288, 484.154, 484.082, 484.236, 484.884, 484.765`
  - **New View Query (Mean: `72.61`):** `76.446, 71.021, 69.735, 70.163, 69.404, 70.892, 81.938, 74.340, 72.579, 69.595`
  - **New View Query with Additional Indexes (Mean: `72.45`):** `79.556, 70.272, 69.592, 69.421, 70.048, 69.964, 70.645, 72.136, 72.035, 80.816`
  - **Result:** There wasn't a significant difference between `New View Query` and `with Additional Indexes`, so I decided not to add the indexes/constraints in the final solution.

+ As a side note, even though the `public.customers` was not used for the view `public.v_product_orders_by_month`, the primary key `customers_pkey` for `customer_name` column might harm the performance. One should use `id` column as primary key for the following reasons:
  - *Efficiency*: Primary key lookups on an integer column (`id`) are faster compared to lookups on a text column (`customer_name`).
  - *Storage*: Integer values in the `id` column require less storage space compared to storing the full name in the `customer_name` column.
  - *Consistency*: Primary keys ensure uniqueness and prevent the possibility of duplicate values, which may not be guaranteed with the `customer_name` column.
  - *Data integrity*: By having the `id` column as the primary key, any changes or updates to the customer's name can be performed without affecting the primary key value.

+ **Comments on Enriching the Customer Data using the API:**
  To fetch the industry of the 3701 customers, either you have to send a request to the endpoint `https://api.apollo.io/v1/organizations/enrich` 3701 times, or you have to send a request to the endpoint `https://api.apollo.io/api/v1/organizations/bulk_enrich` 371 times because the bulk enrichment allows up to 10 domains. Since a premium account was not provided, I was out of credits with my initial Apollo.io account and had to create two additional Microsoft accounts to fetch all the industries. The Apollo.io default account doesn't let you send more than 100 requests per hour. Also, it prevents you from sending more than 20 requests per minute. First, I split 3701 customer domains into chunks of 10s and fed them through the `bulk_enrich` endpoint. I fed the result to the PostgreSQL, and all operations are done in the Python script.
