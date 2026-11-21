# Namma Krushi SQLite Queries

Useful SQL queries for inspecting the **Namma Krushi** SQLite database with **DB Browser for SQLite**.

> Open **DB Browser for SQLite → Execute SQL**, paste a query, and run it.

## 1. See All Tables

```sql
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;
```

## 2. See All Registered Farmers

```sql
SELECT
    user_id,
    name,
    username,
    language
FROM users
ORDER BY user_id DESC;
```

## 3. See Administrator Accounts

```sql
SELECT
    admin_id,
    username,
    password_hash
FROM admins;
```

The password should appear as a bcrypt hash such as `$2b$...`, not plain text.

## 4. See Disease Predictions with Farmer Details

```sql
SELECT
    d.prediction_id,
    u.name AS farmer,
    u.username,
    d.disease,
    ROUND(d.confidence * 100, 2) AS confidence_percent,
    d.image_path,
    d.created_at
FROM disease_predictions d
JOIN users u
    ON d.user_id = u.user_id
ORDER BY d.created_at DESC;
```

## 5. See Greenhouse Analyses

```sql
SELECT
    g.analysis_id,
    u.name AS farmer,
    g.temperature,
    g.humidity,
    g.soil_moisture,
    g.light_intensity,
    g.co2,
    g.prediction,
    ROUND(g.confidence * 100, 2) AS confidence_percent,
    g.created_at
FROM greenhouse_analyses g
JOIN users u
    ON g.user_id = u.user_id
ORDER BY g.created_at DESC;
```

## 6. See Greenhouse XAI Explanations

```sql
SELECT
    u.name,
    g.prediction,
    g.xai_explanation,
    g.created_at
FROM greenhouse_analyses g
JOIN users u
    ON g.user_id = u.user_id
ORDER BY g.created_at DESC;
```

## 7. See All Chat Sessions

```sql
SELECT
    c.session_id,
    u.name AS farmer,
    c.title,
    c.created_at
FROM chat_sessions c
JOIN users u
    ON c.user_id = u.user_id
ORDER BY c.created_at DESC;
```

## 8. See Complete Chat Messages

```sql
SELECT
    s.title,
    u.name AS farmer,
    m.role,
    m.message,
    m.created_at
FROM chat_messages m
JOIN chat_sessions s
    ON m.session_id = s.session_id
JOIN users u
    ON s.user_id = u.user_id
ORDER BY s.session_id, m.created_at;
```

## 9. Most Commonly Detected Diseases

```sql
SELECT
    disease,
    COUNT(*) AS total_predictions
FROM disease_predictions
GROUP BY disease
ORDER BY total_predictions DESC;
```

## 10. Greenhouse Condition Distribution

```sql
SELECT
    prediction,
    COUNT(*) AS total
FROM greenhouse_analyses
GROUP BY prediction
ORDER BY total DESC;
```

## 11. Quick Admin Dashboard Statistics

```sql
SELECT
    (SELECT COUNT(*) FROM users) AS total_farmers,
    (SELECT COUNT(*) FROM disease_predictions) AS disease_predictions,
    (SELECT COUNT(*) FROM greenhouse_analyses) AS greenhouse_analyses,
    (SELECT COUNT(*) FROM chat_sessions) AS chat_sessions,
    (SELECT COUNT(*) FROM chat_messages) AS chat_messages;
```

## 12. See Activity for Each Farmer

```sql
SELECT
    u.user_id,
    u.name,
    u.username,

    (
        SELECT COUNT(*)
        FROM disease_predictions d
        WHERE d.user_id = u.user_id
    ) AS disease_checks,

    (
        SELECT COUNT(*)
        FROM greenhouse_analyses g
        WHERE g.user_id = u.user_id
    ) AS greenhouse_checks,

    (
        SELECT COUNT(*)
        FROM chat_sessions c
        WHERE c.user_id = u.user_id
    ) AS chats

FROM users u
ORDER BY u.user_id;
```

## 13. Latest Disease Predictions

```sql
SELECT
    d.prediction_id,
    u.name AS farmer,
    d.disease,
    ROUND(d.confidence * 100, 2) AS confidence_percent,
    d.created_at
FROM disease_predictions d
JOIN users u
    ON d.user_id = u.user_id
ORDER BY d.created_at DESC
LIMIT 10;
```

## 14. Latest Greenhouse Analyses

```sql
SELECT
    g.analysis_id,
    u.name AS farmer,
    g.prediction,
    ROUND(g.confidence * 100, 2) AS confidence_percent,
    g.created_at
FROM greenhouse_analyses g
JOIN users u
    ON g.user_id = u.user_id
ORDER BY g.created_at DESC
LIMIT 10;
```

## 15. Count Users by Preferred Language

```sql
SELECT
    language,
    COUNT(*) AS total_users
FROM users
GROUP BY language
ORDER BY total_users DESC;
```

## 16. Count Chat Messages by Role

```sql
SELECT
    role,
    COUNT(*) AS total_messages
FROM chat_messages
GROUP BY role;
```

## Optional: Login History

The current basic schema may not store login timestamps. If login tracking is added later:

```sql
CREATE TABLE IF NOT EXISTS login_history (
    login_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);
```

Then recent logins can be checked with:

```sql
SELECT
    u.name,
    u.username,
    l.login_time
FROM login_history l
JOIN users u
    ON u.user_id = l.user_id
ORDER BY l.login_time DESC;
```

## Notes

- SQLite does not have a traditional database-server login list like MySQL/PostgreSQL.
- DB Browser for SQLite is only a GUI for inspecting the `.db` file.
- Use `SELECT` queries for safe inspection.
- Keep passwords hashed; never store plaintext passwords.

## Verifying Disease Predictions and Admin Dashboard Counts

All data (users, disease predictions, greenhouse analyses **and chat history**) now lives
in the single file `database/namma_krushi.db`. Open only that file in DB Browser.

> **Important:** after running a `SELECT` in DB Browser, close the tab or click **Write Changes**
> (Ctrl+S) so no transaction stays open. An open write transaction blocks the app from saving.
> Never run `DELETE FROM users ...`: `ON DELETE CASCADE` also deletes that farmer's predictions,
> analyses and chats.

### A. The four Admin Dashboard numbers (must match the dashboard exactly)

```sql
SELECT
    (SELECT COUNT(*) FROM users)                                  AS registered_farmers,
    (SELECT COUNT(*) FROM disease_predictions)                    AS disease_predictions,
    (SELECT COUNT(*) FROM greenhouse_analyses)                    AS greenhouse_analyses,
    (SELECT COUNT(*) FROM chat_messages WHERE role = 'user')      AS ai_advisory_interactions;
```

### B. Latest saved disease predictions (with farmer)

```sql
SELECT
    d.prediction_id,
    u.username,
    d.disease,
    ROUND(d.confidence * 100, 2) AS confidence_percent,
    d.image_path,
    d.created_at
FROM disease_predictions d
JOIN users u ON u.user_id = d.user_id
ORDER BY d.prediction_id DESC
LIMIT 10;
```

### C. Detect accidental duplicates (should return no rows)

```sql
SELECT user_id, disease, confidence, COUNT(*) AS copies,
       MIN(created_at) AS first_saved, MAX(created_at) AS last_saved
FROM disease_predictions
GROUP BY user_id, disease, confidence, strftime('%Y-%m-%d %H:%M', created_at)
HAVING COUNT(*) > 1;
```

### D. Predictions per farmer

```sql
SELECT u.username, COUNT(d.prediction_id) AS predictions
FROM users u
LEFT JOIN disease_predictions d ON d.user_id = u.user_id
GROUP BY u.user_id
ORDER BY predictions DESC;
```

### E. AI Advisory questions and answers (latest 10 exchanges)

```sql
SELECT s.user_id, m.session_id, m.role, substr(m.message, 1, 80) AS message, m.created_at
FROM chat_messages m
JOIN chat_sessions s ON s.session_id = m.session_id
ORDER BY m.message_id DESC
LIMIT 20;
```

### F. Database health checks

```sql
PRAGMA foreign_key_check;   -- must return no rows
PRAGMA user_version;        -- 1 = old chat file already imported
```
