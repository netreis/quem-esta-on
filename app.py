import streamlit as st
import subprocess
import platform
import socket
import json
import threading
from queue import Queue
import os


st.set_page_config(page_title="Scanner de Rede Local", page_icon="🔍", layout="wide")

def load_css(css_file):
    if os.path.exists(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("styles/styles.css")


logo_path = "assets/wifi.png"
if os.path.exists(logo_path):
    st.logo(logo_path)
else:
    st.warning("Logotipo não encontrado na pasta assets/wifi.png")


st.title("🔍 Quem Está ON!")
st.write("Varreduroa na rede local para encontrar dispositivos conectados.")


def obter_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        return ip_local
    except Exception:
        return "1192.168.1.1"
    

def pingar_ip(ip_queue, resultados, total_ips, barra_progresso, texto_progresso):
    sistema = platform.system().lower()
    comando = ["ping", "-c", "1", "-W", "1"] if sistema != "windows" else ["ping", "-n", "1", "-w", "1000"]
    
    while not ip_queue.empty():
        ip = ip_queue.get()        
        try:
            resultado = subprocess.run(comando + [ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if resultado.returncode == 0:
                try:
                    nome_host = socket.gethostbyaddr(ip)[0]
                except socket.herror:
                    nome_host = "Desconhecido (renomear)"
                
                resultados.append({
                    "ip": ip,
                    "status": "Ativo",
                    "hostname": nome_host
                })
        except Exception:
            pass
        
        ip_queue.task_done()
        remanescentes = ip_queue.qsize()
        processados = total_ips - remanescentes
        progresso = processados / total_ips

ip_sugerido = obter_ip_local()
subrede_sugerida = ".".join(ip_sugerido.split(".")[:3]) + ".0"

col1, col2 = st.columns(2)
with col1:
    subrede = st.text_input("Detecção automática da rede local:", value=subrede_sugerida)
with col2:
    num_threads = st.slider("Número de processos. Quanto maior, maior a velocidade e menor a precisão.", min_value=10, max_value=100, value=50)

if st.button("Escanear", type="primary"):
    partes = subrede.split(".")
    if len(partes) == 4:
        base_ip = f"{partes[0]}.{partes[1]}.{partes[2]}."
        fila_ips = Queue()
        for i in range(1, 255):
            fila_ips.put(f"{base_ip}{i}")
        
        total_ips = fila_ips.qsize()
        lista_resultados = []
        texto_status = st.empty()
        barra_progresso = st.progress(0.0)

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(
                target=pingar_ip, 
                args=(fila_ips, lista_resultados, total_ips, barra_progresso, texto_status)
            )
            t.daemon = True
            t.start()
            threads.append(t)
        fila_ips.join()        

        barra_progresso.empty()
        texto_status.success(f"Escaneamento concluído! {len(lista_resultados)} dispositivos encontrados.")
        if lista_resultados:
            st.subheader("Dispositivos Encontrados")
            st.dataframe(lista_resultados, width='stretch')
            json_string = json.dumps(lista_resultados, indent=4, ensure_ascii=False)
            st.download_button(
                label="📥 Baixar Resultados (JSON)",
                data=json_string,
                file_name="dispositivos_rede.json",
                mime="application/json"
            )
        else:
            st.warning("Nenhum dispositivo respondeu ao ping na sub-rede informada.")
    else:
        st.error("Por favor, insira um formato de sub-rede válido (ex: 192.168.1.0).")
