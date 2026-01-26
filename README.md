<div align="center">
  <img src="https://via.placeholder.com/800x200?text=MIMIC+MOCK+API+ENGINE" alt="Mimic Banner" width="100%">
  
  <h1>🎭 Mimic Mock API Engine</h1>
  <p><strong>The "Infrastructure-First" Mocking Engine for .NET 9 & Vue 3</strong></p>

  <p>
    <img src="https://img.shields.io/badge/.NET-9.0-blue?style=for-the-badge&logo=dotnet" alt="dotnet">
    <img src="https://img.shields.io/badge/Vue.js-3.0-green?style=for-the-badge&logo=vuedotjs" alt="vue">
    <img src="https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker" alt="docker">
    <img src="https://img.shields.io/badge/Maintained_by-hoysengleang-orange?style=for-the-badge" alt="maintainer">
  </p>

  <p>
    <a href="#-overview">Overview</a> •
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-project-structure">Structure</a> •
    <a href="./CONTRIBUTING.md">Contributing</a>
  </p>
</div>

<hr />

## 📖 Overview
<b>Mimic</b> is a professional-grade mocking engine designed to eliminate backend bottlenecks. Built with <b>.NET 9 Minimal APIs</b>, it intercepts dynamic routes and serves custom JSON responses with simulated latency and specific HTTP status codes.

---

## 🚀 Quick Start (Flexible Setup)
Mimic offers a frictionless onboarding experience. Choose the method that fits your environment:

<table>
  <tr>
    <td width="50%">
      <h3>🐳 Docker-Only (Recommended)</h3>
      No local SDKs required. Our containers include .NET 9 and Node.js.
      <br><br>
      <code>docker compose up --build</code>
    </td>
    <td width="50%">
      <h3>💻 Local SDK Way</h3>
      For native debugging and full IDE IntelliSense. Requires .NET 9 SDK.
      <br><br>
      <code>./setups/setup.sh</code>
    </td>
  </tr>
</table>

---

## 📂 Project Structure


| Folder | Responsibility |
| :--- | :--- |
| `src/Mimic.API` | **Backend**: .NET 9 Core Engine & Middleware. |
| `src/Mimic.UI` | **Frontend**: Vue 3 Dashboard (Vite + TS). |
| `setups/` | **Automation**: Shell and PowerShell setup scripts. |
| `docker-compose.yml` | **Orchestration**: Global stack configuration. |

<hr />

<div align="center">
  <p>Maintained by <b><a href="https://github.com/hoysengleang">hoysengleang</a></b></p>
</div>
