import os
import logging
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, Column, String, DateTime, Integer

keycloak_url = os.getenv("KEYCLOAK_URL")
client_id = os.getenv("CLIENT_ID")
username = os.getenv("USER")
keycloak_password = os.getenv("PASSWORD").strip().replace("\n", "")
older = int(os.getenv("OLDER"))

Base = declarative_base()
password = os.getenv("POSTGRES_PASSWORD").strip().replace("\n", "")
engine = create_engine(f'postgresql+psycopg2://'
                       f'{os.getenv("POSTGRES_USER")}:{password}@{os.getenv("POSTGRES_HOST")}'
                       f':{os.getenv("POSTGRES_PORT")}/{os.getenv("POSTGRES_DB")}')
Session = sessionmaker(bind=engine)


class MyTable(Base):
    __tablename__ = "notebooks"
    notebook_id = Column(String, primary_key=True)
    user_id = Column(String)
    last_accessed = Column(DateTime)
    created_at = Column(DateTime)
    description = Column(String)
    port = Column(Integer)
    dataset_name = Column(String)
    dataset_user = Column(String)
    notebook_type = Column(String)


def get_notebooks():
    with Session() as session:
        instances = session.query(MyTable).all()
        return instances


def get_token() -> str | None:
    payload = {
        "client_id": client_id,
        "username": username,
        "password": keycloak_password,
        "grant_type": "password",
    }

    response = requests.post(keycloak_url, data=payload)

    if response.status_code == 200:
        token_info = response.json()
        access_token = token_info['access_token']
        return access_token
    else:
        return None
    

def delete_datasets(data, token: str) -> int:
    errors = 0
    for entry in data:
        date = datetime.strptime(entry["last_accessed"], "%Y-%m-%d %H:%M:%S")
        current_date = datetime.now()

        difference = current_date - date

        if difference < timedelta(days=older):
            continue

        notebooks = get_notebooks()
        find = False
        for notebook in notebooks:
            if notebook.dataset_name == entry["name"] and notebook.dataset_user == entry["user"]:
                find = True
                break

        if find:
            continue

        go_response = requests.delete(f"https://ingress.sedimark.work/balancer/delete_path?path={entry["user"]}/{entry["name"]}&temp=false",
                                      headers={
                                        "Authorization": f"Bearer {token}"
                                      })

        neo4j_response = requests.delete(f"https://ingress.sedimark.work/neo4j/dataset/delete?name={entry["name"]}&user={entry["user"]}",
                                 headers={
                                    "Authorization": f"Bearer {token}"
                                 })
        
        if go_response.status_code == 200 and neo4j_response.status_code == 200:
            logging.info("Dataset deleted successuflly!")
        else:
            logging.error(go_response.json(), "\n", neo4j_response.json())
            errors += 1
    
    return errors


def main():
    token = get_token()

    if token is None:
        logging.error("Error getting the token!")
        return

    response = requests.get("https://ingress.sedimark.work/neo4j/datasets/all", 
                            headers={
                                "Authorization": f"Bearer {token}"
                            })

    if response.status_code != 200:
        logging.error("Error getting the datasets!")
        return

    errors = delete_datasets(response.json(), token)

    if errors > 0:
        delete_datasets(response.json(), token)


if __name__ == '__main__':
    main()
