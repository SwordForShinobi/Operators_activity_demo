import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
import io
import requests
from datetime import datetime, timedelta
import os

# Настройка страницы
st.set_page_config(page_title="Dashboard операторы", layout="wide")

# Пути к файлам истории
script_dir = Path(__file__).parent
HISTORY_FILE = script_dir / 'history.csv'

# Функция сохранения выгрузки в историю
def save_to_history(df, date):
    """Сохраняет данные в history.csv, добавляя колонку date"""
    df_copy = df.copy()
    df_copy['date'] = date
    
    if HISTORY_FILE.exists():
        # Читаем существующий файл
        history_df = pd.read_csv(HISTORY_FILE)
        # Проверяем, есть ли уже данные за эту дату
        if date in history_df['date'].values:
            # Уже есть данные за сегодня - не дублируем
            return False
        # Дописываем новые данные
        pd.concat([history_df, df_copy], ignore_index=True).to_csv(HISTORY_FILE, index=False)
        return True
    else:
        df_copy.to_csv(HISTORY_FILE, index=False)
        return True

# Функция загрузки данных из API
def fetch_api_data():
    """Запрос к API"""
    api_url = "https://azs.knp24.ru/api/v1/reports/workers"
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data)
    return df

# Функция загрузки истории
def load_history():
    """Загружает историю из CSV"""
    if HISTORY_FILE.exists():
        return pd.read_csv(HISTORY_FILE)
    return pd.DataFrame()

# Заголовок
st.title("📊 Дэшборд операторов АЗС")

# Проверка: есть ли данные за сегодня
today_str = datetime.now().strftime('%Y-%m-%d')
history_df = load_history()
today_data_exists = False

if not history_df.empty:
    today_data_exists = today_str in history_df['date'].values

# Если данных за сегодня нет — загружаем из API (фолбэк, если планировщик не сработал)
if not today_data_exists:
    with st.spinner('📡 Загрузка данных из API...'):
        try:
            df_today = fetch_api_data()
            saved = save_to_history(df_today, today_str)
            if saved:
                st.toast(f'✅ Данные за {today_str} загружены и сохранены в историю', icon='✅')
                # Обновляем историю
                history_df = load_history()
        except Exception as e:
            st.error(f"⚠️ Ошибка загрузки данных из API: {e}")
            if history_df.empty:
                st.error("Нет данных ни в API, ни в истории.")
                st.stop()

# Выбор периода
st.sidebar.header("📅 Период выгрузки")

# Даты по умолчанию: с начала текущего месяца по сегодня
today = datetime.now().date()
first_day_of_month = today.replace(day=1)

date_range = st.sidebar.date_input(
    "Выберите период:",
    value=(first_day_of_month, today),
    min_value=datetime(2024, 1, 1).date(),
    max_value=today,
    format="DD.MM.YYYY"
)

# Обработка выбора периода
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, datetime):
    start_date = end_date = date_range.date()
else:
    start_date = first_day_of_month
    end_date = today

# Загрузка истории и фильтрация по периоду
history_df = load_history()

if not history_df.empty:
    # Фильтруем по датам
    history_df['date'] = pd.to_datetime(history_df['date']).dt.date
    mask = (history_df['date'] >= start_date) & (history_df['date'] <= end_date)
    df_period = history_df[mask].copy()
    
    if df_period.empty:
        st.warning(f"Нет данных за период {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
        st.stop()
    
    # Суммируем данные за период по операторам
    # Проверяем наличие колонки Oplacheno_SBP
    agg_columns = {
        'Total_cheks': 'sum',
        'Promo_cheks': 'sum',
        'Promo_by_Coffee_Fuel': 'sum',
        'Promo_by_Card': 'sum',
        'Non_Promo_cheks': 'sum',
        'Total_Bonus_cards': 'sum',
    }
    if 'Oplacheno_SBP' in df_period.columns:
        agg_columns['Oplacheno_SBP'] = 'sum'
    if 'Proc_clientov_s_kartami' in df_period.columns:
        agg_columns['Proc_clientov_s_kartami'] = 'mean'
    
    df = df_period.groupby(['AZS', 'Filial_name', 'Id_Filiala', 'Id_bedolagi', 'Name_bedolagi'], as_index=False).agg(agg_columns)
else:
    st.warning("История пуста. Загрузите данные из API.")
    st.stop()

# Инициализация session_state для выбранного оператора
if 'selected_operator' not in st.session_state:
    st.session_state.selected_operator = None

# Отображение выбранного периода
st.sidebar.info(f"**С:** {start_date.strftime('%d.%m.%Y')}\n\n**По:** {end_date.strftime('%d.%m.%Y')}")

# Боковая панель с фильтрами
st.sidebar.header("Фильтры")

# 1. Фильтр по всем филиалам
filials = sorted(df['Filial_name'].unique())
filial_options = ['Все филиалы'] + filials

# Находим индекс Центрального филиала для старта
central_index = 0
if 'Центральный' in filials:
    central_index = filial_options.index('Центральный')

selected_filial = st.sidebar.selectbox(
    "🏢 Выберите филиал:",
    options=filial_options,
    index=central_index
)

# Фильтрация по филиалу
if selected_filial == 'Все филиалы':
    df_filial = df.copy()
else:
    df_filial = df[df['Filial_name'] == selected_filial]

# Выбор АЗС
all_azs = sorted(df_filial['AZS'].unique())
selected_azs = st.sidebar.multiselect(
    "⛽ Выберите АЗС:",
    options=all_azs,
    default=all_azs
)

# Фильтрация по выбранным АЗС
if selected_azs:
    df_azs = df_filial[df_filial['AZS'].isin(selected_azs)]
else:
    df_azs = df_filial.copy()

# 3. Фильтр по акциям
promo_filter = st.sidebar.radio(
    "🏷️ Тип акций:",
    options=['Все', 'Coffee & Fuel', 'Big Races'],
    index=0,
    horizontal=True
)

# Определяем колонку с акциями в зависимости от фильтра
if promo_filter == 'Coffee & Fuel':
    promo_column = 'Promo_by_Coffee_Fuel'
    promo_label = 'Coffee & Fuel'
elif promo_filter == 'Big Races':
    promo_column = 'Promo_by_Card'
    promo_label = 'Big Races'
else:  # 'Все акции'
    promo_column = 'Promo_cheks'
    promo_label = 'Все акции (Coffee&Fuel + Big Races)'

# Блок "Лидеры филиала" — только если выбран конкретный филиал
if selected_filial != 'Все филиалы':
    st.divider()
    st.subheader("🏆 Лидеры филиала")

    # Рассчитываем процент промо-чеков для каждого оператора
    df_leaders = df_azs.copy()
    df_leaders['promo_percent'] = (df_leaders[promo_column] / df_leaders['Total_cheks'] * 100).where(df_leaders['Total_cheks'] > 0, 0)

    # Сортируем по проценту промо-чеков и берем топ-3
    df_top3 = df_leaders.nlargest(3, 'promo_percent')

    # Отображаем карточки лидеров
    leader_cols = st.columns(min(len(df_top3), 3))

    for idx, (_, row) in enumerate(df_top3.iterrows()):
        with leader_cols[idx]:
            medal = ["🥇", "🥈", "🥉"][idx]
            st.info(
                f"{medal} **{row['Name_bedolagi']}**\n\n"
                f"📍 АЗС: {row['AZS']}\n\n"
                f"🏷️ Промо: **{row['promo_percent']:.1f}%**\n\n"
                f"📊 {int(row[promo_column])} из {int(row['Total_cheks'])} чеков"
            )

# Список операторов (bedolagi)
operators = sorted(df_azs['Name_bedolagi'].unique())

# Если выбранный оператор не в текущем списке, сбрасываем
if st.session_state.selected_operator not in operators:
    st.session_state.selected_operator = operators[0] if operators else None

selected_operator = st.session_state.selected_operator

# Основной контент
st.subheader("👥 Выберите оператора")
if selected_operator:
    st.info(f"**Выбран оператор:** {selected_operator} | 🏷️ Фильтр: {promo_label}")

# Интерактивный выбор операторов - компактные кнопки
num_cols = min(len(operators), 6)
cols = st.columns(num_cols)

for i, operator in enumerate(operators):
    with cols[i % num_cols]:
        is_selected = operator == selected_operator
        button_type = "primary" if is_selected else "secondary"
        
        # Расчет процента акционных чеков (с учётом фильтра по акциям)
        op_data = df_azs[df_azs['Name_bedolagi'] == operator].iloc[0]
        current_promo = op_data[promo_column] if promo_column in op_data.index else op_data['Promo_cheks']
        promo_percent = (current_promo / op_data['Total_cheks'] * 100) if op_data['Total_cheks'] > 0 else 0

        # Расчет доли оплаты по СБП
        if 'Oplacheno_SBP' in op_data.index:
            sbp_percent = (op_data['Oplacheno_SBP'] / op_data['Total_cheks'] * 100) if op_data['Total_cheks'] > 0 else 0
        else:
            sbp_percent = 0
        
        if st.button(
            f"{operator}\n🏷️ **{promo_percent:.0f}% Promo**\n💳 {sbp_percent:.0f}% SBP",
            key=f"op_{operator}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_operator = operator
            st.rerun()

# График
st.divider()
st.subheader(f"📈 Структура чеков по операторам ({promo_label})")

# Подготовка данных для графика с учётом фильтра по акциям
# Сохраняем также АЗС для каждого оператора
df_chart = df_azs.groupby(['Name_bedolagi', 'AZS'], as_index=False).agg({
    'Total_cheks': 'sum',
    'Promo_cheks': 'sum',
    'Promo_by_Coffee_Fuel': 'sum',
    'Promo_by_Card': 'sum',
    'Non_Promo_cheks': 'sum'
}).sort_values('Total_cheks', ascending=False)

# Вычисляем Current_Promo в зависимости от выбранного фильтра
df_chart['Current_Promo'] = df_chart[promo_column] if promo_column in df_chart.columns else df_chart['Promo_cheks']
# Используем готовую колонку Non_Promo_cheks из данных
df_chart['Current_Non_Promo'] = df_chart['Non_Promo_cheks']

# Создание стэк-диаграммы
fig = go.Figure()

# Цвета для каждого оператора
colors_non_promo = []
colors_promo = []

for operator in df_chart['Name_bedolagi']:
    if operator == selected_operator:
        colors_non_promo.append('#DC143C')  # Красный для выбранного
        colors_promo.append('#22C55E')      # Зелёный для выбранного
    else:
        colors_non_promo.append('#FFB6B6')  # Бледный красный для невыбранных
        colors_promo.append('#86EFD1')      # Бледный зелёный для невыбранных

# Добавляем текст для hover с ФИО и АЗС
df_chart['hover_text'] = '<b>' + df_chart['Name_bedolagi'] + '</b><br>АЗС: ' + df_chart['AZS'].astype(str)

# Для unified hover нужно задать customdata на одну серию и использовать hovertemplate
fig.add_trace(go.Bar(
    x=df_chart['Name_bedolagi'],
    y=df_chart['Current_Non_Promo'],
    name='Non-Promo',
    marker_color=colors_non_promo,
    customdata=df_chart['hover_text'],
    hovertemplate='Non-Promo: %{y}<extra></extra>'
))

fig.add_trace(go.Bar(
    x=df_chart['Name_bedolagi'],
    y=df_chart['Current_Promo'],
    name='Promo',
    marker_color=colors_promo,
    customdata=df_chart['hover_text'],
    hovertemplate='%{customdata}<br>Promo: %{y}<extra></extra>'
))

fig.update_layout(
    barmode='stack',
    xaxis_title="Оператор",
    yaxis_title="Количество чеков",
    height=500,
    showlegend=True,
    legend_title_text="Тип чека",
    hovermode='x unified',
    xaxis_tickangle=-45
)

st.plotly_chart(fig, use_container_width=True)

# Вторая диаграмма по филиалам (если выбраны все филиалы)
if selected_filial == 'Все филиалы':
    st.divider()
    st.subheader(f"🏢 Структура чеков по филиалам ({promo_label})")
    
    # Подготовка данных по филиалам
    df_filial_chart = df_azs.groupby('Filial_name', as_index=False).agg({
        'Total_cheks': 'sum',
        'Promo_cheks': 'sum',
        'Promo_by_Coffee_Fuel': 'sum',
        'Promo_by_Card': 'sum',
        'Non_Promo_cheks': 'sum'
    }).sort_values('Total_cheks', ascending=False)
    
    # Вычисляем Current_Promo и Current_Non_Promo для филиалов
    df_filial_chart['Current_Promo'] = df_filial_chart[promo_column] if promo_column in df_filial_chart.columns else df_filial_chart['Promo_cheks']
    df_filial_chart['Current_Non_Promo'] = df_filial_chart['Non_Promo_cheks']
    
    # Вычисляем процент Promo от всех чеков
    df_filial_chart['Promo_Percent'] = (df_filial_chart['Current_Promo'] / df_filial_chart['Total_cheks'] * 100).round(1)
    df_filial_chart['Promo_Percent'] = df_filial_chart['Promo_Percent'].fillna(0).astype(str) + '%'

    # Создание стэк-диаграммы по филиалам
    fig_filials = go.Figure()

    # Цвета для филиалов
    colors_filials_non_promo = ['#FFB6B6' for _ in df_filial_chart['Filial_name']]
    colors_filials_promo = ['#86EFD1' for _ in df_filial_chart['Filial_name']]

    fig_filials.add_trace(go.Bar(
        x=df_filial_chart['Filial_name'],
        y=df_filial_chart['Current_Non_Promo'],
        name='Non-Promo',
        marker_color=colors_filials_non_promo,
        hovertemplate='<b>%{x}</b><br>Non-Promo: %{y}<extra></extra>'
    ))

    fig_filials.add_trace(go.Bar(
        x=df_filial_chart['Filial_name'],
        y=df_filial_chart['Current_Promo'],
        name='Promo',
        marker_color=colors_filials_promo,
        hovertemplate='<b>%{x}</b><br>Promo: %{y}<br>% Promo от всех чеков: ' + df_filial_chart['Promo_Percent'] + '<extra></extra>'
    ))
    
    fig_filials.update_layout(
        barmode='stack',
        xaxis_title="Филиал",
        yaxis_title="Количество чеков",
        height=500,
        showlegend=True,
        legend_title_text="Тип чека",
        hovermode='x unified',
        xaxis_tickangle=-45
    )
    
    st.plotly_chart(fig_filials, use_container_width=True)

# Детальная таблица
st.divider()
st.subheader(f"📋 Детальные данные за период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")

# 2. Добавляем процент клиентов с бонус картами и разделение по акциям
display_df = df_azs.groupby(['Name_bedolagi', 'Filial_name', 'AZS'], as_index=False).agg({
    'Total_cheks': 'sum',
    'Promo_cheks': 'sum',
    'Promo_by_Coffee_Fuel': 'sum',
    'Promo_by_Card': 'sum',
    'Non_Promo_cheks': 'sum',
    'Total_Bonus_cards': 'sum',
    'Proc_clientov_s_kartami': 'mean'
}).sort_values('Total_cheks', ascending=False)

# Переименовываем колонки
display_df = display_df.rename(columns={
    'Name_bedolagi': 'Оператор',
    'Filial_name': 'Филиал',
    'AZS': 'АЗС',
    'Total_cheks': 'Всего чеков',
    'Promo_cheks': 'Promo (все)',
    'Promo_by_Coffee_Fuel': 'Coffee & Fuel',
    'Promo_by_Card': 'Big Races',
    'Non_Promo_cheks': 'Non-Promo',
    'Total_Bonus_cards': 'Бонусные карты',
    'Proc_clientov_s_kartami': '% Клиентов с картами'
})

# Округляем процент до 2 знаков
display_df['% Клиентов с картами'] = display_df['% Клиентов с картами'].round(2)

# Всегда показываем все колонки
display_columns = ['Оператор', 'Филиал', 'АЗС', 'Всего чеков', 'Promo (все)', 'Coffee & Fuel', 'Big Races', 'Non-Promo', 'Бонусные карты', '% Клиентов с картами']
display_df = display_df[display_columns]

# Стилизация таблицы с выделением выбранного оператора и форматированием
def highlight_selected(row):
    if row['Оператор'] == selected_operator:
        return ['background-color: #22C55E33'] * len(row)
    else:
        return [''] * len(row)

# Форматируем процент до 2 знаков после запятой
styled_df = display_df.style.apply(highlight_selected, axis=1).format({
    '% Клиентов с картами': '{:.2f}'
})
st.dataframe(styled_df, use_container_width=True, hide_index=True)

# Кнопка выгрузки в Excel
st.divider()

# Подготовка данных для выгрузки (без стилей)
export_df = df_azs.groupby(['Name_bedolagi', 'Filial_name', 'AZS'], as_index=False).agg({
    'Total_cheks': 'sum',
    'Promo_cheks': 'sum',
    'Promo_by_Coffee_Fuel': 'sum',
    'Promo_by_Card': 'sum',
    'Non_Promo_cheks': 'sum',
    'Total_Bonus_cards': 'sum',
    'Proc_clientov_s_kartami': 'mean'
}).sort_values('Total_cheks', ascending=False)

export_df = export_df.rename(columns={
    'Name_bedolagi': 'Оператор',
    'Filial_name': 'Филиал',
    'AZS': 'АЗС',
    'Total_cheks': 'Всего чеков',
    'Promo_cheks': 'Promo (все)',
    'Promo_by_Coffee_Fuel': 'Coffee & Fuel',
    'Promo_by_Card': 'Big Races',
    'Non_Promo_cheks': 'Non-Promo',
    'Total_Bonus_cards': 'Бонусные карты',
    'Proc_clientov_s_kartami': '% Клиентов с картами'
})

export_df['% Клиентов с картами'] = [round(i, 2) for i in export_df['% Клиентов с картами']]

# Всегда экспортируем все колонки
export_columns = ['Оператор', 'Филиал', 'АЗС', 'Всего чеков', 'Promo (все)', 'Coffee & Fuel', 'Big Races', 'Non-Promo', 'Бонусные карты', '% Клиентов с картами']
export_df = export_df[export_columns]

# Создаем Excel файл в памяти
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    export_df.to_excel(writer, index=False, sheet_name='Данные')

# Формируем имя файла с периодом
filial_name = selected_filial.replace(' ', '_') if selected_filial != 'Все филиалы' else 'all_filials'
period_str = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
st.download_button(
    label="📥 Скачать таблицу в .xlsx",
    data=buffer.getvalue(),
    file_name=f"operators_data_{filial_name}_{period_str}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
