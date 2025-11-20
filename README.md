# Запуск проекта локально

```shell
python .\finance_planner\manage.py migrate            # миграция локальной бд
python .\finance_planner\manage.py bootstrap_dev_data # бутстрап (очищение бд и наполнение тестовыми данными)
python .\finance_planner\manage.py runserver          # запуск сервера
```

## Предустановленные пользователи
### Главный тестовый пользователь
```plain
owner
password123
```
### Другие пользователи
```plain
admin
admin123
```
```plain
stranger
password123
```
