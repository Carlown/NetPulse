# -*- coding: utf-8 -*-
"""Russian language pack for NetPulse.

The host keeps its normal Chinese/English resource pairs.  This plugin wraps
both translation entry points and also refreshes widgets which were created
before the plugin was enabled.  The replacement table deliberately contains
both sides of every pair so it works with either host language setting.
"""

from __future__ import annotations

import re
import sys


_TRANSLATIONS = {}


def _add(ru: str, *sources: str) -> None:
    for source in sources:
        if isinstance(source, str) and source:
            _TRANSLATIONS[source] = ru


# Dashboard and navigation.
_add("Главная", "主页", "Home")
_add("Стресс-тест", "压力测试", "Stress Test")
_add("Совместное тестирование", "协同测试", "Collaborative", "Collaborative Testing")
_add("Монитор", "监控面板", "Monitor")
_add("Плагины", "插件", "Plugins")
_add("Настройки", "设置", "Settings")
_add("Быстрый старт", "快速开始", "Quick Start")
_add("Настройте цель -> подтвердите разрешение -> запустите",
     "配置目标 → 确认授权 → 开始测试",
     "Configure target → Confirm authorization → Start")
_add("Запустить стресс-тест", "开始压力测试", "Start Stress Test")
_add("Последний тест", "最近测试", "Recent Test")
_add("Тесты еще не запускались", "尚无测试记录", "No test has been run yet")
_add("Открыть стресс-тест", "查看压力测试", "View Stress Test")
_add("Загрузка ЦП", "CPU 使用率", "CPU Usage")
_add("Использование памяти", "内存使用率", "Memory Usage")
_add("Загрузка", "下行速率", "Download")
_add("Отдача", "上行速率", "Upload")
_add("Динамика системных ресурсов", "系统资源趋势", "System Resource Trend")
_add("Текущий тест", "当前测试", "Current Test")
_add("Запуск, ожидание данных...", "正在启动，等待实时数据...", "Starting, waiting for live data...")
_add("Остановка, ожидание сводки...", "正在停止，等待汇总结果...", "Stopping, waiting for summary...")
_add("Последний результат", "最近结果", "Latest Result")
_add("Сводный отчет", "汇总报告", "Summary Report")
_add("Копировать сводку", "复制摘要", "Copy Summary")
_add("Экспорт отчета", "导出报告", "Export Report")
_add("Тест еще не выполнялся.", "尚未执行测试。", "No test executed yet.")

# Stress-test page.
_add("Конфигурация цели", "目标配置", "Target Configuration")
_add("Цели (по одному адресу в строке; несколько целей запускаются параллельно)",
     "目标地址（每行一个，支持多目标同时测试）",
     "Targets (one per line; multiple targets run in parallel)")
_add("Цель", "目标", "Target")
_add("Адрес цели отсутствует", "缺少目标地址", "Target address is missing")
_add("Адрес цели слишком длинный", "目标地址过长", "Target address is too long")
_add("Недопустимый адрес цели", "目标地址无效", "Target address is invalid")
_add("Порт", "端口", "Port")
_add("Протокол", "协议", "Protocol")
_add("Потоки", "线程", "Threads")
_add("Количество параллельных потоков (для каждой цели)", "并发线程数（每目标）", "Concurrency Threads (per target)")
_add("Скорость", "速率", "Rate")
_add("Предельная скорость (QPS)", "速率上限(QPS)", "Rate Limit (QPS)")
_add("Длительность", "持续时间", "Duration")
_add("Секунды", "秒", "sec")
_add("Минуты", "分钟", "min")
_add("Часы", "小时", "hour")
_add("Дни", "天", "day")
_add("Заголовки (HTTP, необязательно)", "请求头(HTTP, 可选)", "Headers (HTTP, optional)")
_add("Заголовки должны быть объектом JSON, например {\"User-Agent\": \"NetPulse\"}",
     "请求头必须是 JSON 对象，例如 {\"User-Agent\": \"NetPulse\"}",
     "Headers must be a JSON object, for example {\"User-Agent\": \"NetPulse\"}")
_add("Заголовки должны быть корректным JSON", "请求头须为合法 JSON", "Headers must be valid JSON")
_add("Заголовки должны быть объектом JSON", "请求头必须是 JSON 对象", "Headers must be a JSON object")
_add("Количество или размер заголовков превышает ограничение", "请求头数量或大小超出限制", "Headers exceed the count or size limit")
_add("Цели плагина", "插件目标", "Plugin Targets")
_add("Авторизованные цели", "已授权目标", "Authorized Targets")
_add("Очистить", "清空", "Clear")
_add("Очистить авторизации", "清空授权记录", "Clear Authorizations")
_add("Удалить все сохраненные авторизации целей? Их потребуется подтвердить заново при следующем тесте.",
     "将删除本机保存的全部目标授权。下次测试这些目标时需要重新确认，是否继续？",
     "All saved target authorizations will be removed. You will need to confirm them again before the next test. Continue?")
_add("Все авторизации целей очищены", "已清空全部目标授权记录", "All target authorizations cleared")
_add("Записи авторизаций целей удалены", "目标授权记录已删除", "Target authorizations removed")
_add("Статус", "运行状态", "Status")
_add("Готово", "就绪", "Ready")
_add("Отправлено", "已发送", "Sent")
_add("Успешно", "成功", "Success")
_add("Средняя задержка (мс)", "平均延迟(ms)", "Avg Latency (ms)")
_add("Активные потоки", "活跃线程", "Active Threads")
_add("Всего отправлено", "总发送流量", "Total Sent Traffic")
_add("Последняя причина ошибки: —", "最近失败原因：—", "Last error: —")
_add("Начать", "开始测试", "Start")
_add("Остановить", "停止测试", "Stop")
_add("Тест выполняется...", "测试进行中...", "Test in progress...")
_add("Запуск...", "启动中...", "Starting...")
_add("Запуск стресс-теста...", "正在启动压测...", "Starting stress test...")
_add("Остановка...", "正在停止...", "Stopping...")
_add("Ожидание завершения потоков worker", "等待 worker 线程退出", "Waiting for worker threads to exit")
_add("Тест остановлен вручную", "手动停止压测", "Stress test stopped manually")
_add("Завершено", "已完成", "Completed")
_add("Импортированные цели", "已导入目标", "Targets imported")
_add("Сводка отчета скопирована в буфер обмена", "报告摘要已复制到剪贴板", "Report summary copied to clipboard")
_add("Выберите формат", "选择导出格式", "Choose format")
_add("Нет целей", "无目标", "No targets")
_add("Плагин не вернул целей", "该插件未返回任何目标", "The plugin returned no targets")
_add("Нет отчета", "暂无报告", "No report")
_add("Сначала выполните стресс-тест", "请先执行一次压测", "Run a stress test first")
_add("В текущем отчете нет данных для копирования", "当前报告没有可复制的内容", "The current report has no content to copy")
_add("Тест еще не выполнялся.", "尚未执行测试。", "No test executed yet.")
_add("Нет данных", "暂无数据", "No data")
_add("Ничего", "（暂无）", "(none)")
_add("Нет", "无", "N/A")
_add("Ожидание...", "等待中...", "waiting...")
_add("Подсказка: сначала подтвердите авторизацию каждой цели; скорость и параллелизм ограничиваются токен-бакетом.",
     "提示：所有目标须先通过授权确认；速率与并发受令牌桶限速保护。",
     "Note: every target requires authorization; rate is capped by token bucket.")

# Validation, import/export, and common notifications.
_add("Недопустимая конфигурация", "配置无效", "Invalid Config")
_add("В файле конфигурации отсутствует адрес цели", "配置文件缺少目标地址", "Config file is missing targets")
_add("Невозможно экспортировать", "无法导出", "Cannot Export")
_add("Перед экспортом укажите хотя бы один адрес цели", "请至少填写一个目标地址", "Enter at least one target before exporting")
_add("Невозможно импортировать", "无法导入", "Cannot Import")
_add("Тест выполняется. Сначала остановите его", "测试正在运行中，请先停止", "Test is running; stop it first")
_add("Ошибка импорта", "导入失败", "Import Failed", "Import failed")
_add("Недопустимый формат файла конфигурации", "配置文件格式无效", "Config file has invalid format")
_add("Уведомление о версии", "版本提示", "Version Notice")
_add("Экспорт конфигурации", "导出配置", "Export Config")
_add("Импорт конфигурации", "导入配置", "Import Config")
_add("Конфигурация JSON (*.json)", "JSON 配置 (*.json)", "JSON Config (*.json)")
_add("Конфигурация JSON (*.json);;Все файлы (*.*)", "JSON 配置 (*.json);;所有文件 (*.*)", "JSON Config (*.json);;All Files (*.*)")
_add("Все файлы (*.*)", "所有文件 (*.*)", "All Files (*.*)", "All files (*.*)")
_add("Экспорт выполнен", "导出成功", "Exported")
_add("Ошибка экспорта", "导出失败", "Export Failed", "Export failed")
_add("Ошибка очистки", "清空失败", "Clear Failed")
_add("Сохранено", "已保存", "Saved")
_add("Скопировано", "已复制", "Copied")
_add("Скопировано", "复制成功", "Copy successful")
_add("Ошибка копирования", "复制失败", "Copy Failed")
_add("Очищено", "已清空", "Cleared")
_add("Ошибка запуска", "启动失败", "Start failed")
_add("Не удалось запустить стресс-тест, проверьте конфигурацию", "无法启动压测，请检查配置", "Cannot start stress test, check configuration")
_add("Высокая скорость не подтверждена, тест отменен", "高速率未确认，测试已取消", "High rate not confirmed; cancelled")
_add("Не удалось получить цели плагина", "插件目标获取失败", "Plugin target fetch failed")

# Collaborative testing.
_add("Совместное тестирование", "协同测试", "Collaborative Testing", "Collaborative")
_add("Роль", "角色", "Role")
_add("Главный узел (создать приглашение)", "主控（发起邀请）", "Host (invite)")
_add("Узел (присоединиться)", "节点（加入）", "Node (join)")
_add("Подключение", "连接方式", "Connection")
_add("Ретранслятор (рекомендуется для WAN)", "中继（外网推荐）", "Relay (WAN)")
_add("Прямое (локальная сеть)", "直连（局域网）", "Direct (LAN)")
_add("Создать сеанс", "发起协同", "Host a Session")
_add("Максимум узлов", "最大节点数", "Max Nodes")
_add("Присоединиться к сеансу", "加入协同", "Join a Session")
_add("Код приглашения", "邀请码", "Invite Code")
_add("Название узла", "节点名称", "Node Name")
_add("Статус узлов", "节点状态", "Node Status")
_add("Всего запросов", "累计请求", "Total Requests")
_add("Всего успешных", "累计成功", "Total Success")
_add("QPS в реальном времени", "实时 QPS", "Live QPS")
_add("Журнал совместного тестирования", "协同日志", "Collab Log")
_add("Сгенерировать приглашение", "生成邀请码", "Generate Invite")
_add("Скопировать LAN-адрес", "复制局域网地址", "Copy LAN Address")
_add("Перезапустить от имени администратора и открыть брандмауэр", "以管理员重启并放行防火墙", "Restart as admin to open firewall")
_add("Начать трансляцию (использовать конфигурацию стресс-теста)", "广播开始（使用压测页配置）", "Broadcast Start (uses Stress config)")
_add("Остановить трансляцию", "广播停止", "Broadcast Stop")
_add("Адрес главного узла (LAN IP, порт необязательно)", "主控地址（局域网 IP，可带端口）", "Host address (LAN IP, port optional)")
_add("Присоединиться", "加入", "Join")
_add("Выйти", "退出", "Leave")
_add("Нет подключенных узлов", "（暂无节点连接）", "(no nodes connected)")
_add("Скопировать журнал", "复制日志", "Copy Log")
_add("Пусто", "（暂无）", "(empty)")
_add("Приглашение для совместного теста создано", "生成协同邀请码", "Collab invite generated")
_add("Начало совместной трансляции", "广播协同开始", "Collab start broadcast")
_add("Подключение...", "正在连接...", "Connecting...")
_add("Вышли", "已退出", "Left")
_add("Получена команда главного узла, запуск теста", "收到主控指令，开始压测", "Received host command; starting")
_add("Получена команда главного узла, остановка теста", "收到主控指令，停止压测", "Received host command; stopping")
_add("Ретранслятор MQTT (broker.hivemq.com)", "公共 MQTT 中继 (broker.hivemq.com)", "Public MQTT relay (broker.hivemq.com)", "public MQTT relay (broker.hivemq.com)")
_add("Прямой режим: узлы должны находиться в одной локальной сети с главным узлом.", "直连模式：节点需与主控在同一局域网。", "Direct mode: nodes must be on the same LAN as the host.")
_add("Прямой режим: укажите LAN IP главного узла.", "直连模式：请填写主控的局域网 IP 地址。", "Direct mode: enter the host's LAN IP address.")
_add("Приглашение создано (прямой режим LAN)", "已生成邀请码（局域网直连模式）", "Invite generated (LAN direct mode)")
_add("Подключение к ретранслятору истекло; проверьте сеть и повторите попытку", "连接中继服务器超时，请检查网络后重试", "Relay connection timed out; check your network and retry")
_add("Приглашение истекло", "邀请码已失效", "Invite code expired")
_add("Этот код приглашения истек; новые узлы не смогут присоединиться. Создайте новое приглашение.", "该邀请码已过期，新节点无法使用它加入。如需邀请新节点，请重新生成邀请码。", "This invite code has expired; new nodes can no longer join with it. Generate a new invite to add nodes.")
_add("Нет узлов онлайн", "暂无在线节点", "No Online Nodes")
_add("Дождитесь подключения хотя бы одного узла и затем отправьте команду начала.", "请等待至少一个节点加入后再广播开始指令。", "Wait for at least one node to join before broadcasting a start command.")
_add("Неверный ввод", "参数错误", "Invalid input")
_add("Сначала укажите цель на странице стресс-теста", "请先在压测页填写目标", "Set the target on the Stress page first")
_add("Подтверждение высокой скорости", "高请求速率二次确认", "High Rate Confirmation")
_add("Укажите код приглашения", "请填写邀请码", "Invite code required")
_add("Укажите адрес главного узла", "请填写主控地址", "Host address required")
_add("Запрос разрешения администратора для открытия брандмауэра.", "请求管理员权限重启以放行防火墙。", "Requesting admin restart to open firewall.")
_add("Недостаточно прав", "未授权", "Not elevated")
_add("UAC отклонен; брандмауэр не открыт", "您拒绝了 UAC 授权，防火墙未能放行", "UAC denied; firewall not opened")
_add("Ошибка", "失败", "Failed")
_add("Отменено", "已取消", "Cancelled")
_add("Не удалось сохранить авторизацию", "授权保存失败", "Authorization Save Failed")
_add("Высокая скорость не подтверждена; трансляция отменена", "高速率未确认，广播已取消", "High rate not confirmed; broadcast cancelled")
_add("Подключение к главному узлу...", "正在连接主控...", "Connecting to host...")
_add("Неверная конфигурация", "配置格式错误", "Malformed configuration")
_add("Недопустимая команда запуска", "启动指令无效", "Invalid Start Command")
_add("Ожидание потоков worker", "等待 worker 线程退出", "Waiting for worker threads to exit")
_add("Код приглашения истек (подключенные узлы не затронуты; новые узлы присоединиться не смогут)", "⏱ 邀请码已过期（已加入节点不受影响，新节点无法加入）", "⏱ Invite code expired (joined nodes stay connected; new nodes cannot join)")
_add("Остановка трансляции", "已广播停止", "Stop broadcast")
_add("Не удалось определить публичный IP (рекомендуется режим ретранслятора)", "无法探测公网 IP（建议切换到中继模式）", "Cannot detect public IP (consider switching to Relay mode)")
_add("Ожидание...", "等待中...", "waiting...")

# Disclaimer and main window/tray.
_add("Отказ от ответственности и условия использования", "免责声明与使用条款", "Disclaimer & Terms of Use")
_add("Я прочитал(а) и согласен(на) со всеми условиями", "我已知晓并同意以上全部条款", "I have read and agree to all terms above")
_add("Принять", "接受", "Accept")
_add("Выход", "退出", "Exit")
_add("Подтверждение авторизации цели", "目标授权确认", "Target Authorization")
_add("Я владею этой целью или имею письменное разрешение ее владельца", "我确认拥有该目标，或已获得目标所有者的书面授权", "I own this target or have written authorization from its owner")
_add("Я понимаю, что несанкционированное стресс-тестирование незаконно и принимаю всю ответственность", "我理解未授权压测属违法行为，并愿意承担全部法律责任", "I understand unauthorized stress testing is illegal and I accept full liability")
_add("Примечание об авторизации (обязательно, например: собственный сервер / номер договора)", "授权说明（必填，如：自有服务器 / 合同编号等）", "Authorization note (required, e.g. own server / contract no.)")
_add("Подтвердить", "确认授权", "Confirm")
_add("Отмена", "取消", "Cancel")
_add("Подключено", "已加入", "Joined")
_add("Недействительный код приглашения или комната заполнена", "邀请码无效或已满员", "Invalid code or room full")
_add("Тайм-аут подключения", "连接超时", "Connection timeout")
_add("Соединение с главным узлом разорвано", "与主控断开连接", "Disconnected from host")
_add("Подключено (режим ретранслятора)", "已加入（中继模式）", "Joined (relay mode)")
_add("Подключено (публичный режим ретранслятора)", "已加入（公共中继模式）", "Joined (public relay mode)")
_add("Соединение с ретранслятором разорвано", "与中继服务器断开连接", "Disconnected from relay server")
_add("Код приглашения истек", "邀请码已过期", "Invite code expired")
_add("Не удалось присоединиться", "加入失败", "Join failed")
_add("Недействительный код приглашения или комната заполнена", "邀请码无效或房间已满", "Invalid code or room full")
_add("Главный узел закрыл комнату", "主控已关闭房间", "Host closed the room")
_add("Шлюз UPnP не найден", "未发现 UPnP 网关", "No UPnP gateway found")
_add("💡 Код приглашения действителен 5 минут после создания; присоединитесь в течение этого времени", "💡 邀请码生成后 5 分钟内有效，请在有效期内加入", "💡 Invite code is valid for 5 minutes after generation; join within that window")
_add("Неверные заголовки", "请求头格式错误", "Invalid headers")
_add("Конфигурация главного узла должна быть объектом", "主控配置必须是对象", "Host configuration must be an object")
_add("Нет журнала", "暂无日志", "No log")
_add("Память %", "内存 %", "Memory %")
_add("Инструмент авторизованного сетевого стресс-тестирования и мониторинга производительности", "合法授权网络压力测试与性能监控工具", "Authorized Network Stress Testing & Performance Monitoring")
_add("Процесс публикации (бесплатно, сервер не нужен):\n1. Выберите локальный плагин и значок;\n2. При первом нажатии «Опубликовать» браузер откроется для разовой авторизации;\n3. После этого публикация выполняется одним нажатием и станет доступна после слияния PR.", "上架流程（免费，无需服务器）：\n1. 选择要发布的本地插件和图标；\n2. 首次点击\"一键发布\"会打开浏览器，点一次\"授权\"即可；\n3. 之后每次发布只需一键，PR 合并后即上架。", "How publishing works (free, no server):\n1. Pick the local plugin and icon;\n2. The first \"Publish\" click opens your browser for a one-time authorization;\n3. After that every publish is one click. It goes live once the PR is merged.")
_add("ghp_xxxxxxxxxxxx (public_repo, workflow permissions)", "ghp_xxxxxxxxxxxx（public_repo, workflow 权限）", "ghp_xxxxxxxxxxxx (public_repo, workflow)")
_add("Ошибка перезагрузки", "重载失败", "Reload failed")
_add("Импортировано", "导入成功", "Imported")
_add("Установить", "安装", "Install")
_add("Резервная копия экспортирована", "备份已导出", "Backup Exported")
_add("Восстановить резервную копию настроек", "恢复设置备份", "Restore settings backup", "Restore Settings Backup")
_add("Резервная копия JSON (*.json);;Все файлы (*.*)", "JSON 设置备份 (*.json);;所有文件 (*.*)", "JSON settings backup (*.json);;All files (*.*)")
_add("Безопасные параметры из резервной копии заменят текущие. Перед восстановлением будет создан settings.json.bak; авторизованные цели, токены, данные плагинов и история тестов не изменятся. Продолжить?", "将使用备份中的安全偏好覆盖当前偏好。恢复前会自动创建 settings.json.bak；授权目标、访问令牌、插件私有数据和测试历史不会改变。是否继续？", "Safe preferences in the backup will replace the current preferences. A settings.json.bak file will be created first; authorized targets, access tokens, private plugin data and test history will not change. Continue?")
_add("Файлы журналов (*.log *.txt)", "日志文件 (*.log *.txt)", "Log files (*.log *.txt)")
_add("Журнал аудита", "审计日志", "Audit Log")
_add("О программе", "关于", "About")
_add("Только для законного авторизованного тестирования производительности.", "仅用于合法授权的性能测试。", "For legally authorized testing only.")
_add("Автор", "作者", "Author")
_add("Укажите хотя бы один адрес цели", "请至少输入一个目标地址", "Enter at least one target")
_add("Показать главное окно", "显示主窗口", "Show Window")
_add("Выйти из программы", "退出", "Quit")
_add("Программа свернута в системный трей; для выхода щелкните правой кнопкой значок трея", "程序已最小化到托盘，右键托盘图标可退出", "Minimized to tray, right-click tray icon to quit")
_add("Подождите...", "请稍候...", "Please wait...")

# Monitor page.
_add("Временное окно", "时间窗", "Window")
_add("1 мин", "1 分钟", "1 min")
_add("5 мин", "5 分钟", "5 min")
_add("15 мин", "15 分钟", "15 min")
_add("Приостановить графики", "暂停绘图", "Pause Charts")
_add("Продолжить графики", "继续绘图", "Resume Charts")
_add("Очистить историю", "清空历史", "Clear History")
_add("Экспорт CSV", "导出 CSV", "Export CSV")
_add("Память", "内存", "Memory")
_add("TCP-соединения", "TCP 连接数", "TCP Connections")
_add("Процессы", "进程数", "Processes")
_add("Тренд CPU / памяти", "CPU / 内存趋势", "CPU / Memory Trend")
_add("Сетевой трафик", "网络速率", "Network Throughput")
_add("Загрузка, КБ/с", "下行 KB/s", "Download KB/s")
_add("Отдача, КБ/с", "上行 KB/s", "Upload KB/s")
_add("Нет разрешения", "无权限", "N/A")
_add("Данные мониторинга экспортированы", "导出监控数据", "Export monitoring data")
_add("Файлы CSV (*.csv)", "CSV 文件 (*.csv)", "CSV files (*.csv)")
_add("Нет доступной истории мониторинга", "当前没有可导出的监控历史", "There is no monitoring history to export")

# Settings page.
_add("Внешний вид", "外观", "Appearance")
_add("Темный режим", "深色模式", "Dark mode")
_add("Темная тема Fluent", "Fluent 深色主题", "Fluent dark theme")
_add("Цвет темы", "主题颜色", "Theme color")
_add("Акцентный цвет кнопок и элементов; применяется сразу", "按钮、进度环等强调色，选择后立即生效", "Accent color for buttons and highlights; applies instantly")
_add("Анимация страниц", "页面动画", "Page animations")
_add("Включить переходы страниц и последовательное появление элементов", "启用页面切换和控件依次浮现效果", "Enable page transitions and staggered control reveals")
_add("Сворачивать в трей при закрытии", "关闭时最小化到托盘", "Minimize to tray on close")
_add("При закрытии окна приложение останется в системном трее", "关闭窗口时程序将驻留系统托盘", "Keep app running in system tray when closing window")
_add("Автоматически проверять обновления при запуске", "启动时自动检查更新", "Auto-check for updates on launch")
_add("Показывать уведомление о новой версии", "发现新版本时弹窗提示", "Show notification when new version is available")
_add("Автоматически (система)", "跟随系统", "Auto (system)", "System")
_add("Упрощенный китайский", "简体中文", "Simplified Chinese")
_add("Язык интерфейса", "界面语言", "Language")
_add("Автоматически выбирать язык системы (по умолчанию)", "跟随系统语言自动选择（默认）", "Auto-follow system language (default)")
_add("Параметры по умолчанию", "默认参数", "Defaults")
_add("Потоки по умолчанию", "默认并发线程", "Default concurrency")
_add("Начальное число потоков для новых сеансов", "新会话的初始线程数", "Initial thread count")
_add("Тайм-аут (мс)", "超时(ms)", "Timeout (ms)")
_add("Тайм-аут отдельного запроса", "单请求超时时间", "Per-request timeout")
_add("Предельная скорость по умолчанию", "默认速率上限(QPS)", "Default rate cap")
_add("Скорость заполнения токен-бакета", "令牌桶填充速率", "Token bucket fill rate")
_add("Длительность по умолчанию (с)", "默认持续时间(秒)", "Default duration (s)")
_add("Начальная длительность теста для новых сеансов", "新会话的初始测试时长", "Initial test duration for new sessions")
_add("Размер пакета по умолчанию (байт)", "默认报文大小(字节)", "Default packet size (bytes)")
_add("Размер полезной нагрузки TCP, UDP и протоколов плагинов", "TCP、UDP 与插件协议的发送载荷大小", "Payload size for TCP, UDP and plugin protocols")
_add("Резервное копирование и диагностика", "备份与诊断", "Backup & Diagnostics")
_add("Резервные копии содержат только внешний вид, язык, параметры теста, трей и обновления; авторизованные цели, прошлые тесты, токены, данные плагинов и история поиска исключены.", "备份仅包含外观、语言、默认测试参数、托盘和更新偏好；不会包含授权目标、上次测试、访问令牌、插件私有数据或搜索历史。", "Backups contain only appearance, language, test defaults, tray and update preferences; authorized targets, previous tests, access tokens, private plugin data and search history are excluded.")
_add("Экспорт резервной копии настроек...", "导出设置备份…", "Export Settings…")
_add("Восстановить резервную копию настроек...", "恢复设置备份…", "Restore Settings…")
_add("Сбросить параметры", "恢复偏好默认", "Reset Preferences")
_add("Копировать диагностику", "复制诊断摘要", "Copy Diagnostics")
_add("Экспортировать журнал", "导出日志", "Export Log", "Export log")
_add("Открыть папку журналов", "打开日志目录", "Open Log Folder")
_add("Просмотреть отказ от ответственности", "查看免责声明", "View Disclaimer")
_add("Проверить обновления", "检查更新", "Check for Updates")
_add("Проверка...", "检查中…", "Checking…")
_add("Язык будет полностью применен после перезапуска", "界面语言将在重启后完全生效", "Language fully applies after restart")
_add("Требуется перезапуск", "需要重启", "Restart Required")
_add("Языковые настройки восстановлены; полностью применятся после перезапуска.", "已恢复语言偏好，界面语言将在重启后完全生效。", "The language preference was restored and will fully apply after restart.")
_add("Экспорт настроек", "导出设置备份", "Export settings backup")
_add("Настройки JSON (*.json)", "JSON 设置备份 (*.json)", "JSON settings backup (*.json)")
_add("Настройки восстановлены", "设置已恢复", "Settings Restored")
_add("Параметры сброшены", "偏好已重置", "Preferences Reset")
_add("Эта операция сбросит внешний вид, язык, тестовые параметры, трей и настройки обновлений. Согласие, авторизованные цели, токены, плагины и их данные не будут удалены. Продолжить?", "将重置外观、语言、默认测试参数、托盘和更新偏好。授权状态、授权目标、访问令牌、插件及其私有数据不会被清除。是否继续？", "This resets appearance, language, test defaults, tray and update preferences. Consent, authorized targets, access tokens, plugins and private plugin data will not be cleared. Continue?")
_add("Темный", "深色", "Dark")
_add("Светлый", "浅色", "Light")
_add("Упакованная версия", "打包版本", "Packaged")
_add("Исходный код", "源码运行", "Source")
_add("Конфиденциальность: токены, авторизованные/тестовые цели, данные плагинов, история поиска и абсолютные пути исключены.", "隐私：已排除令牌、授权目标、测试目标、插件私有数据、搜索历史和本机绝对路径。", "Privacy: tokens, authorized/test targets, private plugin data, search history and absolute local paths are excluded.")
_add("Обезличенная диагностическая сводка скопирована в буфер обмена.", "脱敏诊断摘要已复制到剪贴板。", "The redacted diagnostic summary was copied to the clipboard.")
_add("Сохранить не удалось", "保存失败", "Save Failed")
_add("Неизвестно", "未知", "Unknown")
_add("Да", "是", "Yes")
_add("Нет", "否", "No")
_add("Обезличенная диагностическая сводка", "脱敏诊断摘要", "Redacted Diagnostic Summary")
_add("Создано: ", "生成时间：", "Generated: ")
_add("Версия приложения: ", "应用版本：", "App version: ")
_add("ОС: ", "操作系统：", "OS: ")
_add("Python: ", "Python：", "Python: ")
_add("PySide6 / Qt: ", "PySide6 / Qt：", "PySide6 / Qt: ")
_add("Fluent Widgets: ", "Fluent Widgets：", "Fluent Widgets: ")
_add("Тема / акцент: ", "主题 / 强调色：", "Theme / accent: ")
_add("Язык: ", "语言：", "Language: ")
_add("Анимация страниц: ", "页面动画：", "Page animations: ")
_add("Потоки / тайм-аут / QPS по умолчанию: ", "默认线程 / 超时 / QPS：", "Defaults threads / timeout / QPS: ")
_add("Длительность / пакет по умолчанию: ", "默认时长 / 数据包：", "Default duration / packet: ")
_add("Сворачивание в трей / автообновление: ", "最小化到托盘 / 自动更新：", "Tray minimize / auto update: ")
_add("Папка настроек доступна для записи: ", "设置目录可写：", "Settings directory writable: ")
_add("Журнал аудита: ", "审计日志：", "Audit log: ")
_add("Журнал сбоев: ", "崩溃日志：", "Crash log: ")
_add("Плагины (всего/активные/отключенные/ошибки/не загружены): ", "插件（总数/运行/禁用/错误/未加载）：", "Plugins (total/running/disabled/error/unloaded): ")
_add("Не найдено", "不存在", "Not found")
_add("Пользовательский...", "自定义…", "Custom…")
_add("Выбрать цвет темы", "选择主题颜色", "Choose Theme Color")
_add("Изменить цвет", "编辑颜色", "Edit Color")
_add("Красный", "红", "Red")
_add("Зеленый", "绿", "Green")
_add("Синий", "蓝", "Blue")
_add("Подтвердить", "确定", "OK")
_add("Восстановление не удалось", "恢复失败", "Restore Failed")
_add("Сброс не удался", "重置失败", "Reset Failed")

# Plugin marketplace.
_add("Снять с публикации", "下架", "Unpublish")
_add("Удалить из избранного", "取消收藏", "Remove from favorites")
_add("Добавить в избранное", "收藏插件", "Add to favorites")
_add("Снять плагин с публикации", "下架插件", "Unpublish Plugin")
_add("Перезагрузить", "重载", "Reload")
_add("Удалить", "删除", "Remove")
_add("Запущен", "运行中", "Running")
_add("Отключен", "已禁用", "Disabled", "disabled")
_add("Ошибка загрузки", "加载失败", "Load failed", "load failed")
_add("Не загружен", "未加载", "Not loaded", "not loaded")
_add("Удалить плагин", "删除插件", "Remove Plugin")
_add("Плагины являются сторонним кодом с теми же правами, что и приложение. Устанавливайте только из доверенных источников; отказ от ответственности также применяется.", "插件为第三方代码，拥有与主程序相同的权限，请仅安装可信来源的插件；插件行为同样受免责声明约束。", "Plugins are third-party code with the same privileges as the app. Only install from trusted sources; the disclaimer applies.")
_add("Импортировать плагин...", "导入插件…", "Import Plugin…")
_add("Открыть папку плагинов", "打开插件目录", "Open Plugin Folder")
_add("Повторно сканировать", "重新扫描", "Rescan")
_add("Выберите файл плагина", "选择插件文件", "Select plugin file")
_add("Плагин Python (*.py);;Все файлы (*.*)", "Python 插件 (*.py);;所有文件 (*.*)", "Python plugin (*.py);;All files (*.*)")
_add("Сканирование завершено", "扫描完成", "Rescan done")
_add("Поиск по имени, автору и описанию...", "搜索插件名称、作者、描述…", "Search by name, author, description…")
_add("Поиск плагинов", "搜索插件", "Search plugins")
_add("Показать подсказки поиска", "展开搜索推荐", "Show search suggestions")
_add("Скрыть подсказки поиска", "收起搜索推荐", "Hide search suggestions")
_add("Фильтр типа и состояния установки", "筛选类型和安装状态", "Filter by type and install status")
_add("Только избранное", "仅看收藏", "Favorites only")
_add("Очистить все фильтры", "清除全部筛选", "Clear all filters")
_add("По убыванию (нажмите для переключения)", "倒序（点击切换）", "Descending (click to toggle)")
_add("По возрастанию (нажмите для переключения)", "正序（点击切换）", "Ascending (click to toggle)")
_add("Опубликовать плагин...", "发布插件…", "Publish a Plugin…")
_add("Обновить", "刷新", "Refresh", "Update")
_add("Обновить", "更新", "Update")
_add("Популярные запросы", "热门搜索", "Popular searches")
_add("История поиска", "搜索历史", "Search history")
_add("Очистить все", "全部清空", "Clear all")
_add("Очистить всю историю поиска", "清空全部搜索历史", "Clear all search history")
_add("Рекомендаций нет; введите ключевое слово для поиска", "暂无推荐，可直接输入关键词搜索", "No suggestions yet; type a keyword to search")
_add("Загрузка marketplace...", "正在加载市场…", "Loading marketplace…")
_add(" (офлайн-кэш)", "（离线缓存）", " (offline cache)")
_add("Снимается с публикации...", "下架中…", "Unpublishing…")
_add("Требуется авторизация", "需要授权", "Authorization required")
_add("Снять с публикации не удалось", "下架失败", "Unpublish failed")
_add("Скачивание не удалось", "下载失败", "Download failed")
_add("Опубликовать плагин в marketplace", "发布插件到市场", "Publish to Marketplace")
_add("Без значка", "无图标", "No icon")
_add("Выбрать значок (PNG/JPG)...", "选择图标 (PNG/JPG)…", "Pick Icon (PNG/JPG)…")
_add("Получить токен", "获取 Token", "Get Token")
_add("Опубликовать (1 щелчок)", "一键发布", "Publish (1-Click)")
_add("Копировать JSON", "复制 JSON", "Copy JSON")
_add("Ручная отправка", "手动提交页面", "Manual Submission")
_add("Введите этот код в браузере или нажмите кнопку копирования:", "请在浏览器中输入以下授权码，或直接点击复制：", "Enter this code in your browser, or click to copy:")
_add("Нажмите, чтобы скопировать код", "点击复制授权码", "Click to copy code")
_add("Открыть браузер снова", "重新打开浏览器", "Reopen Browser")
_add("Значок встраивается в индекс как base64 (не более 64 КБ); sha256 используется для проверки целостности. Токен хранится только локально и используется для создания PR.", "图标会以 base64 内嵌进索引（上限 64KB）；sha256 用于完整性校验。Token 仅保存在本地，用于创建 PR。", "Icon is base64-embedded in the index (max 64KB); sha256 for integrity. Token is stored locally and used only to create the PR.")
_add("Закрыть", "关闭", "Close")
_add("Выбрать значок", "选择图标", "Pick an icon")
_add("Изображения (*.png *.jpg *.jpeg)", "图片 (*.png *.jpg *.jpeg)", "Images (*.png *.jpg *.jpeg)")
_add("Запись JSON скопирована в буфер обмена", "条目 JSON 已复制到剪贴板", "Entry JSON copied to clipboard")
_add("Запрос авторизации...", "正在请求授权…", "Requesting authorization…")
_add("Подключение к GitHub...", "正在连接 GitHub…", "Connecting to GitHub…")
_add("Ожидание авторизации в браузере...", "等待浏览器授权…", "Waiting for browser…")
_add("Нажмите Authorize в открытом браузере. Если он не открылся, нажмите «Открыть браузер снова» справа или посетите github.com/login/device и введите код.", "请在打开的浏览器中点击「Authorize」完成授权。若浏览器未自动打开，请点击右侧「重新打开浏览器」，或手动访问 github.com/login/device 并输入代码。", "Click Authorize in the opened browser. If it didn't open, click 'Reopen Browser' on the right or visit github.com/login/device and enter the code.")
_add("Публикация...", "发布中…", "Publishing…")
_add("Загрузка файла плагина...", "正在上传插件文件…", "Uploading plugin file…")
_add("Обновление индекса плагинов...", "正在更新插件索引…", "Updating plugin index…")
_add("Отправка, публикация произойдет автоматически...", "正在提交，将自动上架…", "Submitting, will go live automatically…")
_add("Публикация не удалась", "发布失败", "Publish failed")
_add("Включить", "启用", "Enable")
_add("Включено", "已启用", "Enabled")
_add("Скачивание...", "下载中…", "Downloading…")
_add("Перезагрузка завершена", "重载完成", "Reloaded")
_add("Неизвестная ошибка", "未知错误", "Unknown error")
_add("Удалено", "已删除", "Removed")
_add("Плагин импортирован и включен", "插件已导入并启用", "Plugin imported and enabled")
_add("По времени", "按时间", "Time")
_add("По имени", "按名称", "Name")
_add("По автору", "按作者", "Author")
_add("По версии", "按版本", "Version")
_add("По состоянию", "按状态", "Status")
_add("Удалить эту историю", "删除这条历史", "Delete this search")
_add("Все", "全部", "All")
_add("Снятие с публикации запрещено", "无权下架", "Unpublish not allowed")
_add("Только автор плагина может снять его с публикации.", "只有插件作者可以下架自己的插件。", "Only the plugin publisher can unpublish this plugin.")
_add("Плагин снят с публикации", "下架成功", "Unpublished")
_add("Установлено", "安装成功", "Installed")
_add("Ошибка установки", "安装失败", "Install failed")
_add("Локальные плагины", "本地插件", "Local Plugins", "Local plugins")
_add("Marketplace", "插件市场", "Marketplace")
_add("Категория", "插件分类", "Category")
_add("GitHub Token", "GitHub Token")
_add("Значок слишком большой", "图标过大", "Icon too large")
_add("Невозможно опубликовать", "无法发布", "Cannot publish")
_add("Сначала выберите локальный плагин", "请先选择一个本地插件", "Please select a local plugin first")
_add("Браузер не открылся", "浏览器未打开", "Browser didn't open")
_add("Нажмите «Открыть браузер снова» или скопируйте код вручную", "请点击「重新打开浏览器」按钮或手动复制代码", "Click 'Reopen Browser' or copy the code manually")
_add("Файл плагина отсутствует", "插件文件缺失", "Plugin file missing")
_add("Исходный файл плагина не найден", "找不到插件源文件", "Cannot find plugin source file")
_add("Проверка автоматической публикации...", "正在检查自动上架配置…", "Checking auto-publish setup…")
_add("Обнаружен доступ на запись в репозиторий, публикация напрямую...", "检测到仓库写权限，直接上架…", "Write access detected, publishing directly…")
_add("Опубликовано", "发布成功", "Published")
_add("Плагин опубликован. Другие пользователи увидят его после обновления marketplace.", "插件已直接上架，其他用户刷新市场即可看到。", "Plugin is now live. Other users will see it after refreshing the marketplace.")
_add("Плагин отправлен и автоматически появится в течение нескольких секунд.", "插件已提交，将在几秒内自动上架。", "Plugin submitted. It will go live automatically within seconds.")
_add("Установлено", "已安装", "Installed")
_add("Плагинов пока нет. Используйте «Импортировать плагин...» или поместите .py в папку плагинов и повторите сканирование.", "暂无插件。点击\"导入插件…\"添加 .py 插件文件，或将插件放入插件目录后重新扫描。", "No plugins yet. Use \"Import Plugin…\" to add a .py file, or drop plugins into the folder and rescan.")
_add("Сначала опубликуйте плагин для авторизации; для снятия с публикации также требуется учетная запись GitHub.", "请先发布一个插件完成授权，下架也需要 GitHub 身份。", "Publish a plugin first to complete authorization; unpublish also requires GitHub identity.")
_add("Не удалось прочитать", "读取失败", "Read failed")
_add("Сначала подтвердите авторизацию в браузере или укажите GitHub Token", "首次发布请在浏览器中确认授权，或填写 GitHub Token", "Confirm authorization in the browser for the first publish, or enter a GitHub Token")
_add("Авторизация требует обновления. Снимите плагин с публикации еще раз.", "授权已过期，请重新下架以完成授权。", "Authorization needs refresh. Please unpublish again to re-authorize.")
_add("Авторизация требует обновления. Опубликуйте плагин еще раз.", "授权已过期，请重新发布以完成授权。", "Authorization needs refresh. Please publish again to re-authorize.")
_add("Средний", "中", "en")
_add("Английский", "English")
_add("Подключение к публичному ретранслятору...", "Connecting to public relay server...")
_add("Ошибка: отсутствует библиотека paho-mqtt, выполните pip install paho-mqtt", "Error: paho-mqtt missing, run: pip install paho-mqtt")
_add("Ошибка: отсутствует библиотека paho-mqtt", "Error: paho-mqtt missing")
_add("Комната заполнена", "Room full")
_add("Недействительный код приглашения", "Invalid invite code")
_add("Плагин импортирован, но загрузка не удалась; проверьте код", "Imported but failed to load; check plugin code")
_add("Исходный путь не найден", "Source path not found")
_add("Недопустимый путь плагина", "Invalid plugin path")
_add("Запись плагина не найдена", "Plugin record not found")
_add("Плагин-папка должен содержать main.py", "Folder plugin must contain main.py")
_add("Поддерживаются только файлы плагинов .py", "Only .py plugin files supported")
_add("Нет журнала совместного тестирования для копирования", "There is no collaborative log to copy")
_add("Подключение к ретранслятору...", "Connecting to relay server...")
_add("Подождите", "Please wait")
_add("ЦП %", "CPU %")
_add("Рынок плагинов", "Marketplace")
_add("Токен GitHub", "GitHub Token")
_add("Виджеты Fluent: ", "Fluent Widgets: ")
_add("Экспортировать отчет", "Export report")
_add("с", "s")

# Updates.
_add("Пропустить эту версию (больше не напоминать)", "跳过此版本（不再提示本次更新）", "Skip this version (don't remind me again)")
_add("Больше не проверять обновления автоматически", "不再自动检查更新", "Don't check for updates automatically")
_add("Обновить", "去更新", "Update")
_add("Позже", "稍后再说", "Later")
_add("Ошибка проверки обновлений", "检查更新失败", "Update check failed")
_add("Версия актуальна", "已是最新版本", "Up to date")

# Labels stored in tuple constants (market filters) and engine error codes.
_add("Инструменты", "工具", "Tools")
_add("Протоколы", "协议", "Protocols")
_add("Интерфейс и страницы", "界面", "UI & Pages")
_add("Прочее", "其他", "Misc")
_add("Все", "全部", "All")
_add("Все состояния", "全部状态", "All states")
_add("Не установлено", "未安装", "Not installed")
_add("Доступно обновление", "可更新", "Updates available")
_add("Тайм-аут", "超时", "Timeout")
_add("Соединение отклонено", "连接被拒", "Connection refused")
_add("Соединение сброшено", "连接被重置", "Connection reset")
_add("Сеть недоступна", "网络不可达", "Unreachable")
_add("Ошибка разрешения DNS", "DNS 解析失败", "DNS resolution failed")
_add("Ошибка рукопожатия TLS", "TLS 握手失败", "TLS handshake failed")
_add("Ошибка сертификата", "证书错误", "Certificate error")
_add("Соединение закрыто", "连接已关闭", "Connection closed")
_add("Ошибка соединения", "连接错误", "Connection error")
_add("Нет ответа ICMP", "ICMP 无响应", "ICMP no reply")

# Common source fragments used in dynamic status strings and hard-coded UI.
_FRAGMENTS = {
    "插件已加载：": "Плагин загружен: ", "插件已卸载：": "Плагин выгружен: ",
    "插件已导入：": "Плагин импортирован: ", "插件加载失败：": "Ошибка загрузки плагина: ",
    "插件导入但加载失败，请检查插件代码": "Плагин импортирован, но загрузка не удалась; проверьте код",
    "插件记录未找到": "Запись плагина не найдена", "源路径不存在": "Исходный путь не найден",
    "无效的插件路径": "Недопустимый путь плагина", "文件夹插件必须包含 main.py": "Плагин-папка должен содержать main.py",
    "仅支持 .py 插件文件": "Поддерживаются только файлы плагинов .py", "复制失败：": "Ошибка копирования: ",
    "插件删除失败：": "Ошибка удаления плагина: ", "插件指标回调失败: ": "Ошибка callback метрик плагина: ",
    "插件 on_test_start 回调失败: ": "Ошибка callback on_test_start плагина: ",
    "插件 on_test_end 回调失败: ": "Ошибка callback on_test_end плагина: ",
    "插件目标获取失败": "Не удалось получить цели плагина", "连接失败: ": "Ошибка подключения: ",
    "中继连接失败: ": "Ошибка подключения к ретранслятору: ", "连接被拒绝: ": "Подключение отклонено: ",
    "无法连接到 ": "Не удалось подключиться к ", "监听失败: ": "Ошибка прослушивания: ",
    "节点 ": "Узел ", " 已加入": " присоединился", " 已断开": " отключился", " 已退出": " вышел",
    "局域网地址：": "LAN-адрес: ", "  ← 内网节点连这个": "  <- используйте этот адрес для узлов LAN",
    "中继模式已就绪，邀请码 ": "Режим ретранслятора готов, код приглашения ",
    "（通过 ": " (через ", "）": ")", "邀请码 ": "Код приглашения ", " 已复制到剪贴板": " скопирован в буфер обмена",
    "正在连接公共中继服务器...": "Подключение к публичному ретранслятору...",
    "正在连接中继服务器...": "Подключение к ретранслятору...", "请稍候": "Подождите",
    "连接失败": "Ошибка подключения", "房间已满": "Комната заполнена", "邀请码无效": "Недействительный код приглашения",
    "错误：缺少 paho-mqtt 库，请运行 pip install paho-mqtt": "Ошибка: отсутствует библиотека paho-mqtt, выполните pip install paho-mqtt",
    "错误：缺少 paho-mqtt 库": "Ошибка: отсутствует библиотека paho-mqtt",
    "当前没有可复制的协同日志": "Нет журнала совместного тестирования для копирования",
    "正在连接...": "Подключение...", "测试进行中...": "Тест выполняется...", "启动中...": "Запуск...",
    "已完成": "Завершено", "秒": "с", "，": ", ", "×": "x",
    "无法探测公网 IP": "Не удалось определить публичный IP", "检查网络后重试": "проверьте сеть и повторите попытку",
    "发现新版本 ": "Обнаружена новая версия ", "当前版本 v": "Текущая версия v",
    "，GitHub 已发布 ": ", в GitHub опубликована версия ", "。\n是否前往下载更新？": ".\nОткрыть страницу загрузки обновления?",
    "无法连接 GitHub：": "Не удалось подключиться к GitHub: ", "，与 GitHub 最新版本一致。": ", совпадает с последней версией GitHub.",
    "当前筛选：": "Активные фильтры: ", "暂无可安装的插件": "Нет доступных для установки плагинов",
    "没有找到匹配 ": "Не найдено плагинов, соответствующих ", " 的插件，可清空关键词或筛选": "; очистите запрос или фильтры",
    "匹配 ": "Совпадений: ", " 个插件": " плагинов", "共 ": "Всего ",
    "另有 ": "; еще ", " 个需要升级 NetPulse": " требуют более новой версии NetPulse",
    " 个需要升级 NetPulse": " требуют более новой версии NetPulse",
    "当前筛选条件": "активным фильтрам", "市场加载失败：": "Ошибка загрузки marketplace: ",
    "请检查网络后点击": "проверьте сеть и нажмите ", "刷新": "Обновить",
    "（离线缓存）": " (офлайн-кэш)",
    "、": ", ", "；": "; ", "：": ": ",
    " 个目标 · 进度 ": " целей · прогресс ", "成功 ": "успешно ", " / 失败 ": " / ошибок ",
    "进度 ": "Прогресс ", "错误率 ": "ошибок ", "平均 ": "среднее ",
    "剩余 ": "свободно ", "可用": "доступно", "内存": "Память",
}

# Dynamic f-string fragments.  They are kept separate from exact resources so
# addresses, counts, error details and file paths remain untouched.
_EXTRA_FRAGMENTS = {
    "公共 MQTT 中继": "публичный ретранслятор MQTT",
    "公共中继": "публичный ретранслятор",
    "新增授权目标: ": "Добавлена авторизованная цель: ",
    "移除授权目标: ": "Авторизованная цель удалена: ",
    "授权目标保存失败: ": "Не удалось сохранить авторизованную цель: ",
    "授权目标移除保存失败: ": "Не удалось удалить авторизованную цель: ",
    "已广播开始: ": "Начало транслировано: ",
    "已复制 ": "Скопировано ",
    " 条协同日志": " записей журнала совместного тестирования",
    "中继模式：通过 ": "Режим ретранслятора: через ",
    " 中转，支持外网节点加入，无需部署服务器、无需公网 IP。": " для ретрансляции; узлы WAN могут присоединяться без сервера и публичного IP.",
    "中继模式：自动通过 ": "Режим ретранслятора: автоматическое подключение к главному узлу через ",
    " 连接主控，只需输入邀请码，无需填写主控地址。": "; введите только код приглашения, адрес главного узла не нужен.",
    "连接模式已切换为": "Режим подключения переключен на ",
    "，正在按新模式自动重新生成邀请码…": "; приглашение автоматически создается заново.",
    "已生成邀请码 ": "Создан код приглашения ",
    "（中继模式，通过 ": " (режим ретранслятора, через ",
    " 中转）": " для ретрансляции)",
    "外网地址（UPnP 已自动映射）：": "WAN-адрес (автоматическое отображение UPnP): ",
    "  ← 外网节点连这个": "  <- используйте этот адрес для узлов WAN",
    "外网地址（IPv6，无需端口映射，直连可用）：": "WAN-адрес (IPv6, перенаправление порта не требуется, доступно прямое подключение): ",
    "公网 IP：": "Публичный IP: ",
    "（IPv4，需在路由器转发 TCP ": " (IPv4; перенаправьте TCP-порт ",
    " 到本机，或使用中继模式）": " на этот компьютер или используйте режим ретранслятора)",
    "防火墙：已放行 TCP ": "Брандмауэр: TCP-порт разрешен: ",
    "防火墙：尚未放行 TCP ": "Брандмауэр: TCP-порт пока не разрешен: ",
    "，点击下方按钮以管理员身份重启后自动放行": "; нажмите кнопку ниже для перезапуска от имени администратора и автоматического разрешения",
    "协同测试将广播开始：": "Совместное тестирование отправит команду начала: ",
    "每个节点速率上限 ": "предельная скорость каждого узла ",
    "每个目标速率上限 ": "предельная скорость каждой цели ",
    " QPS，当前在线 ": " QPS; сейчас онлайн ",
    " 个节点（合计约 ": " узлов (всего примерно ",
    "合计约 ": "всего примерно ",
    " QPS 同时压向同一目标）。": " QPS одновременно направляются на одну цель).",
    "请再次确认您拥有全部目标授权，且目标可承受该速率。": "Еще раз подтвердите авторизацию всех целей и убедитесь, что цели выдержат эту скорость.",
    "请再次确认您拥有目标授权，且目标可承受该速率。": "Еще раз подтвердите авторизацию цели и убедитесь, что она выдержит эту скорость.",
    "正在创建 ": "Создание ",
    " 个 worker 线程": " потоков worker",
    "节点不支持协议：": "Узел не поддерживает протокол: ",
    "目标 ": "Цель ",
    " 未授权，测试已阻止": " не авторизована, тест заблокирован",
    "无法保存目标 ": "Не удалось сохранить авторизацию цели ",
    " 的授权记录：": ": ",
    "已拒绝无效的主控配置：": "Отклонена недействительная конфигурация главного узла: ",
    "拒绝无效协同启动配置：": "Отклонена недействительная конфигурация запуска совместного теста: ",
    "参数 ": "Параметр ",
    " 不是有效整数": " не является допустимым целым числом",
    " 超出允许范围 ": " вне допустимого диапазона ",
    "⏱ 邀请码有效期：": "⏱ Срок действия кода приглашения: ",
    "分": " мин ",
    "秒（已加入节点不受影响，过期后新节点无法加入）": " с (подключенные узлы не затронуты; после истечения новые узлы не смогут присоединиться)",
    "插件页面创建失败：": "Ошибка создания страницы плагина: ",
    "插件页面注册失败：": "Ошибка регистрации страницы плагина: ",
    "## 新插件提交": "## Отправка нового плагина",
    "新插件提交": "Отправка нового плагина",
    "插件 ID": "ID плагина", "名称": "Название", "版本": "Версия", "作者": "Автор",
    "由 NetPulse 客户端一键发布。": "Опубликовано одним нажатием из клиента NetPulse.",
    "收藏：": "Избранное: ",
    "确定要下架插件「": "Снять плагин с публикации «",
    "」吗？": "»?",
    "将创建一个 Pull Request 从市场索引中移除该插件，PR 合并后插件不再对用户可见。需要 GitHub 授权。": "Будет создан Pull Request для удаления плагина из индекса marketplace; после слияния PR плагин исчезнет у пользователей. Требуется авторизация GitHub.",
    "状态：": "Состояние: ",
    "确定删除插件\"": "Удалить плагин «",
    "\"？插件文件将从磁盘移除。": "»? Файл плагина будет удален с диска.",
    "共加载 ": "Загружено плагинов: ",
    " 个插件": " плагинов",
    "请在浏览器中授权（代码 ": "Авторизуйтесь в браузере (код ",
    "），授权后将自动继续下架。": "); после авторизации снятие с публикации продолжится автоматически.",
    "授权码 ": "Код авторизации ",
    " 已复制": " скопирован",
    "正在 Fork 仓库（": "Создание Fork репозитория (",
    "）…": ")...",
    "插件已重新加载：": "Плагин перезагружен: ",
    "第 ": "Топ-",
    " 名热门搜索：": ": популярный запрос: ",
    "插件 ": "Плагин ",
    " 已从市场下架，其他用户刷新后不再显示。": " снят с публикации в marketplace; после обновления он больше не будет виден.",
    " 的下架请求已提交，将在几秒内自动生效。": ": запрос на снятие отправлен и вступит в силу через несколько секунд.",
    " 已安装并启用": " установлен и включен",
    "上限 64KB，当前 ": "Лимит 64 КБ, сейчас ",
    "KB": " КБ",
    "✓ 已直接上架：": "✓ Опубликовано напрямую: ",
    "✓ 已提交，正在自动上架：": "✓ Отправлено, автоматическая публикация: ",
    "## 下架插件": "## Снятие плагина с публикации",
    "由 NetPulse 插件市场一键下架功能自动创建。": "Создано функцией снятия плагина с публикации в marketplace NetPulse.",
    "已导出 ": "Экспортировано ", " 条监控记录": " записей мониторинга",
    "已恢复 ": "Восстановлено ", " 项偏好；原设置已保存为 ": " параметров; исходные настройки сохранены как ",
    "已写入 ": "Записано ", " 项安全偏好，敏感数据未包含。": " безопасных параметров; конфиденциальные данные не включены.",
    " 已安全忽略 ": " Безопасно пропущено ", " 个非白名单字段。": " полей вне белого списка.",
    "已恢复 ": "Восстановлено ", " 项默认偏好，敏感状态保持不变。": " параметров по умолчанию; конфиденциальное состояние не изменилось.",
    " 条记录": " записей",
    "无法保存动画设置：": "Не удалось сохранить настройки анимации: ",
    "无法写入设置备份：": "Не удалось записать резервную копию настроек: ",
    "备份无效、版本不兼容或无法写入：": "Резервная копия недействительна, несовместима или недоступна для записи: ",
    "无法保存默认偏好：": "Не удалось сохранить параметры по умолчанию: ",
    "可用（": "Доступно (", " 字节）": " байт)",
    "无法生成诊断摘要：": "Не удалось создать диагностическую сводку: ",
    "系统错误 ": "Системная ошибка ",
    "开始压测(": "Запуск стресс-теста (", "目标): ": " целей): ",
    "共 ": "Всего ", " 个目标  |  持续 ": " целей  |  длительность ",
    "持续 ": "длительность ", "总请求 ": "Всего запросов ",
    "合计 ": "Итого ", " 失败 ": " ошибок ", "（错误率 ": " (доля ошибок ",
    "平均延迟 ": "Средняя задержка ", "总发送流量 ": "Всего отправлено ", "速率上限 ": "предельная скорость ",
    "压测完成: total=": "Стресс-тест завершен: всего=", " success=": " успешно=", " fail=": " ошибок=", " errors=": " причины=",
    "来自插件：共 ": "Из плагина: всего ",
    " 个": " элементов",
    "已保存到 ": "Сохранено в ", "配置已导出: ": "Конфигурация экспортирована: ",
    "配置文件来自更新版本的 NetPulse（v": "Файл конфигурации создан более новой версией NetPulse (v",
    "），部分设置可能无法识别。": "); некоторые параметры могут быть неизвестны.",
    "已加载 ": "Загружено ", " 个目标配置": " конфигураций целей", "配置已导入: ": "Конфигурация импортирована: ",
    "配置文件格式错误：": "Недопустимый формат файла конфигурации: ",
    "无法写入文件：": "Не удалось записать файл: ", "无法读取文件：": "Не удалось прочитать файл: ",
    "授权记录无法保存：": "Не удалось сохранить запись авторизации: ",
    "无效目标：": "Недействительная цель: ", "报告已导出: ": "Отчет экспортирован: ",
    "报告已导出(CSV): ": "Отчет экспортирован (CSV): ", "报告已导出(": "Отчет экспортирован (",
    "失败原因分布：": "Распределение причин ошибок: ", "最近失败原因：": "Последняя причина ошибки: ",
    "运行中 · ": "Выполняется · ", " 个目标": " целей",
}
_FRAGMENTS.update(_EXTRA_FRAGMENTS)

for _source, _ru in _FRAGMENTS.items():
    _TRANSLATIONS.setdefault(_source, _ru)

_FRAGMENTS_SORTED = sorted(_FRAGMENTS.items(), key=lambda item: len(item[0]), reverse=True)
_HAN_SUBSTRINGS = sorted(
    ((source, ru) for source, ru in _TRANSLATIONS.items()
     if len(source) >= 2 and any("\u4e00" <= char <= "\u9fff" for char in source)),
    key=lambda item: len(item[0]), reverse=True)


def translate(value):
    """Translate exact strings and dynamic strings while preserving values/URLs."""
    if not isinstance(value, str):
        return value
    direct = _TRANSLATIONS.get(value)
    if direct is not None:
        return direct
    result = value
    for source, ru in _FRAGMENTS_SORTED:
        if source in result:
            result = result.replace(source, ru)
    for source, ru in _HAN_SUBSTRINGS:
        if source in result:
            result = result.replace(source, ru)
    return result


_patched = False
_original = {}


def _swap_refs(old, new):
    for module in list(sys.modules.values()):
        if module is None:
            continue
        try:
            namespace = vars(module)
        except TypeError:
            continue
        for name, value in list(namespace.items()):
            if value is old:
                try:
                    setattr(module, name, new)
                except Exception:
                    pass


def _set_text(getter, setter):
    try:
        value = getter()
        translated = translate(value)
        if translated != value:
            setter(translated)
    except (AttributeError, RuntimeError, TypeError):
        pass


def _convert_widget(widget):
    from PySide6.QtWidgets import QGroupBox, QLineEdit, QPlainTextEdit, QTextEdit

    if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
        _set_text(widget.placeholderText, widget.setPlaceholderText)
    else:
        text = getattr(widget, "text", None)
        set_text = getattr(widget, "setText", None)
        if callable(text) and callable(set_text):
            _set_text(text, set_text)

        item_text = getattr(widget, "itemText", None)
        set_item_text = getattr(widget, "setItemText", None)
        if callable(item_text) and callable(set_item_text):
            try:
                count = widget.count()
            except (AttributeError, RuntimeError, TypeError):
                count = 0
            for index in range(count):
                _set_text(lambda index=index: item_text(index),
                          lambda value, index=index: set_item_text(index, value))

        tab_text = getattr(widget, "tabText", None)
        set_tab_text = getattr(widget, "setTabText", None)
        if callable(tab_text) and callable(set_tab_text):
            try:
                count = widget.count()
            except (AttributeError, RuntimeError, TypeError):
                count = 0
            for index in range(count):
                _set_text(lambda index=index: tab_text(index),
                          lambda value, index=index: set_tab_text(index, value))

        if isinstance(widget, QGroupBox):
            _set_text(widget.title, widget.setTitle)

    try:
        for action in widget.actions():
            _set_text(action.text, action.setText)
            _set_text(action.toolTip, action.setToolTip)
    except (AttributeError, RuntimeError, TypeError):
        pass
    _set_text(widget.toolTip, widget.setToolTip)
    _set_text(widget.windowTitle, widget.setWindowTitle)


def convert_ui():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    for widget in app.allWidgets():
        try:
            _convert_widget(widget)
        except Exception:
            continue


def install():
    global _patched
    if _patched:
        convert_ui()
        return
    import app.services.plugins as plugins_module
    import app.ui.i18n as i18n

    original_l = i18n.L
    original_i18n_text = plugins_module._i18n_text

    def russian_l(zh, en):
        current = original_l(zh, en)
        translated = translate(current)
        if translated == current:
            translated = translate(zh if isinstance(zh, str) else en)
        return translated

    def russian_i18n_text(value):
        current = original_i18n_text(value)
        if isinstance(value, (tuple, list)) and len(value) == 2:
            # Try both tuple sides.  This also handles metadata created while
            # the host is set to English.
            first = translate(value[0])
            second = translate(value[1])
            if first != value[0]:
                return first
            if second != value[1]:
                return second
        return translate(current)

    _original.update(L=original_l, i18n_text=original_i18n_text)
    i18n.L = russian_l
    plugins_module._i18n_text = russian_i18n_text
    _swap_refs(original_l, russian_l)
    _swap_refs(original_i18n_text, russian_i18n_text)
    _patched = True
    convert_ui()


def uninstall():
    global _patched
    if not _patched:
        return
    import app.services.plugins as plugins_module
    import app.ui.i18n as i18n

    original_l = _original.get("L")
    original_i18n_text = _original.get("i18n_text")
    if original_l is not None:
        current_l = i18n.L
        i18n.L = original_l
        _swap_refs(current_l, original_l)
    if original_i18n_text is not None:
        current_i18n_text = plugins_module._i18n_text
        plugins_module._i18n_text = original_i18n_text
        _swap_refs(current_i18n_text, original_i18n_text)
    _original.clear()
    _patched = False


class Plugin(NetPulsePlugin):
    name = ("Русский язык", "Russian Language Pack")
    version = "1.0"
    author = "NetPulse"
    description = (
        "Полный русский перевод интерфейса NetPulse; применяется сразу.",
        "Complete Russian translation of the NetPulse interface; applies immediately.",
    )
    icon = "LANGUAGE"
    category = "ui"

    def on_load(self, ctx):
        self._ctx = ctx
        install()

    def on_unload(self):
        uninstall()

    def create_widget(self, parent):
        from PySide6.QtWidgets import QVBoxLayout, QWidget
        from qfluentwidgets import BodyLabel, InfoBar, PrimaryPushButton, SimpleCardWidget, SubtitleLabel

        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(36, 24, 36, 24)
        layout.setSpacing(12)
        card = SimpleCardWidget(widget)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(10)
        card_layout.addWidget(SubtitleLabel("Русский язык", card))
        card_layout.addWidget(BodyLabel(
            "Русский перевод интерфейса включен. Новые окна, уведомления и динамические статусы также переводятся автоматически.", card))
        button = PrimaryPushButton("Обновить перевод", card)

        def refresh():
            convert_ui()
            InfoBar.success("Перевод обновлен", "Текст интерфейса обновлен.", parent=widget.window(), duration=2500)

        button.clicked.connect(refresh)
        card_layout.addWidget(button)
        layout.addWidget(card)
        layout.addStretch(1)
        return widget
