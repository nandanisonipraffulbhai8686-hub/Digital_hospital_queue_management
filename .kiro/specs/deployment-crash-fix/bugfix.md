# Bugfix Requirements Document

## Introduction

The Digital Hospital Queue Management application crashes immediately on deployment to Railway (and similar cloud platforms such as Render or Fly.io). The deployment log shows "deployment crashed" with no healthy process. The crash is caused by a combination of five issues: the app is started with the Flask development server instead of a production WSGI server, the production WSGI server (`gunicorn`) is absent from `requirements.txt`, all deployment entry-points (`Procfile`, `nixpacks.toml`, `Dockerfile`) invoke `python app.py` which is unsuitable for production, the MongoDB client connects at module import time with a hard-coded `localhost` fallback that is unreachable in a cloud container when `MONGO_URI` is not set, and the APScheduler background scheduler is wired inside `if __name__ == "__main__"` so it never starts when the app is served by gunicorn. A sixth issue — the Flask secret key is hard-coded as `"secret123"` — is a security vulnerability that must also be corrected.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the application is deployed to a cloud platform (e.g., Railway) using the current `Procfile` (`web: python app.py`) THEN the system starts with the Flask built-in development server, which is not designed to handle production traffic and causes the deployment health-check to fail

1.2 WHEN the cloud build step runs `pip install -r requirements.txt` THEN the system fails to install `gunicorn` because it is absent from `requirements.txt`, making it impossible to switch to a production WSGI server without a manual intervention

1.3 WHEN the `Dockerfile` is used to build the container image THEN the system executes `CMD ["python", "app.py"]`, which starts the Flask development server instead of a production-grade server, causing the container to crash or fail health checks in production environments

1.4 WHEN `nixpacks.toml` is used as the build configuration on Railway THEN the system executes `python app.py` as the start command, starting the Flask development server instead of gunicorn

1.5 WHEN the application boots in a cloud container where `MONGO_URI` is not set as an environment variable THEN the system falls back silently to `mongodb://localhost:27017/`, and the `MongoClient(MONGO_URI)` call at module import time in `db.py` either hangs waiting for a connection or raises a connection error before the Flask app can finish initialising, causing the process to crash

1.6 WHEN the application is served by gunicorn (multiple workers) THEN the system never reaches the `if __name__ == "__main__"` block in `app.py`, so `start_reminder_scheduler()` is never called and the APScheduler background job does not run

1.7 WHEN the application runs in any environment THEN the system uses the hard-coded Flask secret key `"secret123"`, which is publicly visible in the repository and allows an attacker to forge signed session cookies

---

### Expected Behavior (Correct)

2.1 WHEN the application is deployed to a cloud platform THEN the system SHALL start via gunicorn (e.g., `gunicorn app:app --bind 0.0.0.0:$PORT`) so that the process is production-grade and passes the platform health check

2.2 WHEN the cloud build step runs `pip install -r requirements.txt` THEN the system SHALL install `gunicorn` because it is listed as a pinned dependency in `requirements.txt`

2.3 WHEN the `Dockerfile` is used to build the container image THEN the system SHALL use `CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]` (or use the `PORT` environment variable) so the container starts a production WSGI server

2.4 WHEN `nixpacks.toml` is used as the build configuration on Railway THEN the system SHALL use `gunicorn app:app --bind 0.0.0.0:$PORT` as the start command

2.5 WHEN the application boots and `MONGO_URI` is not set as an environment variable THEN the system SHALL raise a clear `EnvironmentError` (or equivalent) at startup rather than silently falling back to `localhost`, so the misconfiguration is immediately visible in the deployment logs

2.6 WHEN the application is served by gunicorn THEN the system SHALL start the APScheduler background scheduler through a mechanism that is not gated on `__name__ == "__main__"` (e.g., via a Flask application factory, a gunicorn `post_fork` hook, or a top-level startup call), ensuring reminder jobs run in production

2.7 WHEN the application starts THEN the system SHALL read the Flask secret key exclusively from the `SECRET_KEY` environment variable and SHALL refuse to start (or log a critical warning) if that variable is absent or set to a known-insecure default value

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a patient books, cancels, or reschedules an appointment through the web UI THEN the system SHALL CONTINUE TO persist the appointment correctly in MongoDB Atlas and return the appropriate flash message

3.2 WHEN a valid `MONGO_URI` environment variable is set pointing to a live MongoDB Atlas cluster THEN the system SHALL CONTINUE TO establish the database connection successfully at startup without errors

3.3 WHEN the application is run locally with `python app.py` for development THEN the system SHALL CONTINUE TO start the Flask development server on port 5000 and operate normally (the gunicorn change applies only to the production entry-points)

3.4 WHEN the APScheduler is running in production THEN the system SHALL CONTINUE TO check for upcoming appointments every 60 seconds and send email/SMS reminders 1 hour and 5 minutes before each appointment

3.5 WHEN all required environment variables (`MONGO_URI`, `SECRET_KEY`) are present in the deployment environment THEN the system SHALL CONTINUE TO serve all existing routes (login, register, patient dashboard, doctor dashboard, staff, admin) without any change in behaviour

3.6 WHEN the application handles a session for a logged-in user THEN the system SHALL CONTINUE TO enforce the 30-minute inactivity timeout and redirect to the login page on expiry

---

## Bug Condition Pseudocode

### Bug Condition Functions

```pascal
FUNCTION isBugCondition_NoGunicorn(X)
  INPUT: X represents the deployment configuration
  OUTPUT: boolean
  RETURN (X.procfile_cmd = "python app.py")
      OR (X.nixpacks_start_cmd = "python app.py")
      OR (X.dockerfile_cmd = "python app.py")
END FUNCTION

FUNCTION isBugCondition_MissingGunicornDep(X)
  INPUT: X represents the requirements.txt contents
  OUTPUT: boolean
  RETURN "gunicorn" NOT IN X.packages
END FUNCTION

FUNCTION isBugCondition_MongoURIFallback(X)
  INPUT: X represents the process environment at startup
  OUTPUT: boolean
  RETURN X.env["MONGO_URI"] IS NOT SET
END FUNCTION

FUNCTION isBugCondition_SchedulerNotStarted(X)
  INPUT: X represents the process execution context
  OUTPUT: boolean
  RETURN X.process_name != "__main__"
END FUNCTION

FUNCTION isBugCondition_HardcodedSecretKey(X)
  INPUT: X represents the application configuration
  OUTPUT: boolean
  RETURN X.secret_key = "secret123"
      OR X.secret_key IS NOT READ FROM environment
END FUNCTION
```

### Fix Checking Properties

```pascal
// Property: Production Server is Used
FOR ALL X WHERE isBugCondition_NoGunicorn(X) DO
  result ← deploy(X)
  ASSERT result.server = "gunicorn"
  ASSERT result.health_check = "passed"
END FOR

// Property: gunicorn Dependency Present
FOR ALL X WHERE isBugCondition_MissingGunicornDep(X) DO
  result ← build(X)
  ASSERT "gunicorn" IN result.installed_packages
END FOR

// Property: Missing MONGO_URI Raises Clear Error
FOR ALL X WHERE isBugCondition_MongoURIFallback(X) DO
  result ← start_app(X)
  ASSERT result.error_type = "EnvironmentError"
  ASSERT "MONGO_URI" IN result.error_message
  ASSERT result.fallback_used = false
END FOR

// Property: Scheduler Starts Under gunicorn
FOR ALL X WHERE isBugCondition_SchedulerNotStarted(X) DO
  result ← start_app(X)
  ASSERT result.scheduler_running = true
END FOR

// Property: Secret Key Read from Environment
FOR ALL X WHERE isBugCondition_HardcodedSecretKey(X) DO
  result ← start_app(X)
  ASSERT result.secret_key != "secret123"
  ASSERT result.secret_key = X.env["SECRET_KEY"]
END FOR
```

### Preservation Checking Property

```pascal
// Property: Preservation Checking — all non-buggy inputs unchanged
FOR ALL X WHERE
    NOT isBugCondition_NoGunicorn(X)
    AND NOT isBugCondition_MissingGunicornDep(X)
    AND NOT isBugCondition_MongoURIFallback(X)
    AND NOT isBugCondition_SchedulerNotStarted(X)
    AND NOT isBugCondition_HardcodedSecretKey(X)
DO
  ASSERT F(X) = F'(X)   // application behaviour is identical before and after the fix
END FOR
```
