import configparser
import os

import psycopg2

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_CONFIG = os.path.join(RAIZ, "config.ini")


def ler_config():
    cfg = configparser.ConfigParser()
    if not cfg.read(ARQUIVO_CONFIG, encoding="utf-8"):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {ARQUIVO_CONFIG}")
    return cfg


def _parametros(secao, database=None):
    cfg = ler_config()[secao]
    return dict(
        host=cfg.get("host"),
        port=cfg.getint("port", 5432),
        dbname=database or cfg.get("database"),
        user=cfg.get("user"),
        password=cfg.get("password"),
        connect_timeout=cfg.getint("timeout", 5) if "timeout" in cfg else 5,
        application_name="grupo5_pedidos",
    )


def conectar_consumidor():
    conn = psycopg2.connect(**_parametros("consumidor_grupo5"))
    conn.autocommit = False
    return conn


def conectar_produtor():
    conn = psycopg2.connect(**_parametros("produtor_grupo3"))
    conn.set_session(
        isolation_level=psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ,
        readonly=True,
    )
    return conn


def config_produtor():
    cfg = ler_config()["produtor_grupo3"]
    return cfg.get("schema", "").strip(), cfg.get("view", "vw_integracao_produtos").strip()


def conectar_admin(database="postgres"):
    conn = psycopg2.connect(**_parametros("admin", database=database))
    conn.autocommit = True
    return conn
