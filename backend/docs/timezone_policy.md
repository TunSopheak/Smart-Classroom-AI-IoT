# Timezone Policy

## Display Timezone

The system displays teacher-facing times using:

```text
Asia/Phnom_Penh
```

## Storage Policy

Database timestamps may be stored as UTC internally.

## Reason

UTC is safer for backend storage, but teachers in Cambodia should see local classroom time on the dashboard.
