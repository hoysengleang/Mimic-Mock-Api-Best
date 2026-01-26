<div align="center">
  <h1>🛠️ Contributing to Mimic</h1>
  <p>Help us build the best mocking infrastructure for the developer community.</p>
</div>

<hr />

## 🏗️ Technical Standards

<table>
  <tr>
    <th>Backend (.NET 9)</th>
    <th>Frontend (Vue 3)</th>
  </tr>
  <tr>
    <td>
      <ul>
        <li>Clean Architecture: logic in Services</li>
        <li>Use <b>IOptions</b> for settings</li>
        <li>PascalCase for Methods</li>
        <li>_camelCase for private fields</li>
      </ul>
    </td>
    <td>
      <ul>
        <li>Use <b>script setup</b> syntax</li>
        <li>TypeScript for all components</li>
        <li>Pinia for state management</li>
        <li>Responsive CSS standards</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🌿 Contribution Workflow

### 1. Find Your Task

Check the <b><a href="https://github.com/hoysengleang/Mimic-Mock-Api-Best/projects">Project Board</a></b> for <b>"Todo"</b> items.

### 2. Development Steps

1. **Fork** the repo to your profile.
2. **Clone** and create a feature branch: `git checkout -b feat/your-feature`.
3. **Setup**: Run <code>./setups/setup.sh</code> to configure your `.env`.
4. **Test**: Run <code>docker compose up</code> to verify changes.

### 3. Submission

Open a **Pull Request** to <code>hoysengleang/main</code> and link the issue number (e.g., "Closes #10").

---

<div align="center">
  <p>Questions? <a href="https://github.com/hoysengleang/Mimic-Mock-Api-Best/issues">Open an Issue</a></p>
</div>
