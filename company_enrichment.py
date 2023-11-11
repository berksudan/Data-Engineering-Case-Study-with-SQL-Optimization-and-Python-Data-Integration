import requests
import psycopg2
import time
import sys

COMPANY_BULK_ENRICHMENT_URL = "https://api.apollo.io/api/v1/organizations/bulk_enrich"
BULK_ENRICHMENT_URL_LIMIT = 10
COMPANY_BULK_ENRICHMENT_URL_API_KEY = "AcwrM-4KfSwHzyjfPKjCKA"


def split_list_into_chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_industries_of_domains(domains, cached: bool):
    print('[INFO] Industries are being fetched from the Apollo api..')
    industries = []
    domain_chunks = split_list_into_chunks(lst=domains, n=BULK_ENRICHMENT_URL_LIMIT)
    counter_fetched_industries = 0
    if cached:
        with open('industries.cached') as fp:
            industries = [line[:-1] if line[:-1] != 'None' else None for line in fp]

        return industries
    for domain_chunk in domain_chunks:
        try:
            response = requests.request("POST", COMPANY_BULK_ENRICHMENT_URL,
                                        headers={
                                            'Cache-Control': 'no-cache',
                                            'Content-Type': 'application/json'},
                                        json={
                                            "api_key": COMPANY_BULK_ENRICHMENT_URL_API_KEY,
                                            "domains": domain_chunk
                                        })
            organizations = response.json()['organizations']
        except:
            print(response.text)
            return industries
        for organization in organizations:
            industries.append(
                organization['industry'] if organization is not None and organization['industry'] else None)
        # print('INDUSTRIES:', industries)

        counter_fetched_industries += len(domain_chunk)
        print(f'[INFO] Number of fetched industries: {counter_fetched_industries}/{len(domains)}..')
        time.sleep(4)
    print('[INFO] Industries have been successfully fetched from the Apollo api.')
    return industries


def get_connection():
    try:
        conn = psycopg2.connect(
            database="postgres",
            user="postgres",
            password="Str0ngP@ssw0rd",
            host="127.0.0.1",
            port=5432,
        )
        print("[INFO] Connection to the PostgreSQL established successfully.")
        return conn
    except:
        exit("[ERROR] Connection to the PostgreSQL encountered an error.")


def extract_id_to_contact_domains():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query='SELECT id,contact_email from public.customers;')
    results = cur.fetchall()
    conn.commit()

    cur.close()
    conn.close()

    id_to_contact_domain = {}
    for result in results:
        id_to_contact_domain[result[0]] = result[1].rstrip().split('@')[-1]
    return id_to_contact_domain


def main(cached):
    id_to_contact_domain = extract_id_to_contact_domains()
    id_to_contact_domain = sorted(tuple(id_to_contact_domain.items()))
    contact_ids = [item[0] for item in id_to_contact_domain]
    contact_domains = [item[1] for item in id_to_contact_domain]

    industries = get_industries_of_domains(domains=contact_domains, cached=cached)

    contact_ids_to_industries = list(zip(contact_ids, industries))

    ###################################################################
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query='''
        DROP TABLE IF EXISTS public.industries;
        CREATE TABLE IF NOT EXISTS public.industries (
            id bigint NOT NULL PRIMARY KEY,
            industry text
        );
    ''')
    conn.commit()
    print("[INFO] Table `industries` created successfully.")

    cur.executemany(query='INSERT INTO public.industries (id, industry) VALUES (%s, %s);',
                    vars_list=contact_ids_to_industries)
    conn.commit()
    print("[INFO] Industries inserted to `industries` successfully.")

    cur.execute(query='''
        ALTER TABLE public.customers DROP COLUMN IF EXISTS industry;

        ALTER TABLE public.customers
        ADD COLUMN industry text;

        UPDATE public.customers
        SET industry = public.industries.industry
        FROM public.industries
        WHERE public.customers.id = public.industries.id;
    ''')
    conn.commit()
    print("[INFO] Using the join with `industries`, the industries added as a new column to `customers` successfully.")

    # Closing the cursor and connection
    cur.close()
    conn.close()


if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) >= 2 and sys.argv[1] == '--cached':
        main(cached=True)
    else:
        main(cached=False)
