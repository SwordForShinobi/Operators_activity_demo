# Настройка планировщика задач (Windows Task Scheduler)

## Автоматический запуск скрипта fetch_data.py в 1:00 ежедневно

### Способ 1: Через интерфейс (рекомендуется)

1. **Откройте Планировщик заданий**
   - Нажмите `Win + R`
   - Введите `taskschd.msc`
   - Нажмите Enter

2. **Создайте задачу**
   - В правой панели выберите "Создать задачу..." (не "Создать простую задачу")

3. **Вкладка "Общие"**
   - Имя: `AZS Dashboard Data Fetcher`
   - Описание: `Ежедневная загрузка данных из API в history.csv`
   - ✅ "Выполнять для всех пользователей"
   - ✅ "Выполнять с наивысшими правами"
   - Конфигурация: `Windows 10 / Windows Server 2016`

4. **Вкладка "Триггеры"**
   - Нажмите "Создать..."
   - Начать задачу: `По расписанию`
   - Ежедневно
   - Время: `01:00:00`
   - Повторять каждые: (не заполнять)
   - ✅ "Включено"
   - OK

5. **Вкладка "Действия"**
   - Нажмите "Создать..."
   - Действие: `Запуск программы`
   - Программа или сценарий: путь к Python
     ```
     c:\Users\dBryukhanov\Job_Data\Pyhon_projects\.venv\Scripts\python.exe
     ```
   - Добавить аргументы:
     ```
     "c:\Users\dBryukhanov\Job_Data\Pyhon_projects\Operator_dashbords\fetch_data.py"
     ```
   - Начать в (рабочая папка):
     ```
     c:\Users\dBryukhanov\Job_Data\Pyhon_projects\Operator_dashbords
     ```
   - OK

6. **Вкладка "Условия"**
   - ✅ "Запускать задачу только при питании от электросети" (для сервера можно снять)
   - ❌ "Останавливать задачу если выполнение длится дольше" (снять галочку)

7. **Вкладка "Параметры"**
   - ✅ "Запускать задачу независимо от входа в систему"
   - ✅ "Перезапускать через:" `1 минута`
   - ✅ "Повторять в течение:" `15 минут`
   - ✅ "Если задача не выполняется, перезапустить через:" `5 минут`
   - ✅ "Останавливать задачи, выполняемые дольше:" `1 час`
   - ✅ "Если задача не завершается, принудительно остановить её:" `5 минут`

8. **Вкладка "Вход в систему"** (если есть)
   - Введите пароль вашей учётной записи

9. **Сохраните задачу**
   - Нажмите OK
   - Введите пароль учётной записи Windows

---

### Способ 2: Через командную строку (powershell)

Запустите PowerShell от имени администратора и выполните:

```powershell
$taskName = "AZS Dashboard Data Fetcher"
$pythonPath = "c:\Users\dBryukhanov\Job_Data\Pyhon_projects\.venv\Scripts\python.exe"
$scriptPath = "c:\Users\dBryukhanov\Job_Data\Pyhon_projects\Operator_dashbords\fetch_data.py"
$workingDir = "c:\Users\dBryukhanov\Job_Data\Pyhon_projects\Operator_dashbords"

# Создаём триггер (ежедневно в 1:00)
$trigger = New-ScheduledTaskTrigger -Daily -At 1am

# Создаём действие
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $workingDir

# Создаём настройки
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -ForceStopHidden

# Создаём задачу (замените USERNAME на ваше имя пользователя)
Register-ScheduledTask `
    -TaskName $taskName `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -User "USERNAME" `
    -Password "YOUR_PASSWORD" `
    -RunLevel Highest
```

---

## Проверка работы

### 1. Запустить задачу вручную
- В планировщике найдите задачу `AZS Dashboard Data Fetcher`
- Правая кнопка → "Выполнить"

### 2. Проверьте логи
- Файл лога: `c:\Users\dBryukhanov\Job_Data\Pyhon_projects\Operator_dashbords\fetch_data.log`
- Должно появиться сообщение вида:
  ```
  [2026-03-28 01:00:05] ==================================================
  [2026-03-28 01:00:05] 🚀 Начало загрузки данных из API
  [2026-03-28 01:00:06] 📡 Запрос к API: https://azs.knp24.ru/api/v1/reports/workers
  [2026-03-28 01:00:07] 📦 Получено записей: 548
  [2026-03-28 01:00:07] ✅ Создаём новый файл истории с данными за 2026-03-28
  [2026-03-28 01:00:07] ✅ Загрузка завершена успешно
  ```

### 3. Проверьте history.csv
- Файл: `c:\Users\dBryukhanov\Job_Data\Pyhon_projects\Operator_dashbords\history.csv`
- Должна появиться новая строка с сегодняшней датой

---

## История изменений логов

Для просмотра последних 20 строк лога:
```powershell
Get-Content "c:\Users\dBryukhanov\Job_Data\Pyhon_projects\Operator_dashbords\fetch_data.log" -Tail 20
```

---

## Удаление задачи

```powershell
Unregister-ScheduledTask -TaskName "AZS Dashboard Data Fetcher" -Confirm:$false
```
