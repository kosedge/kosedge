# Copilot Instructions for Kos Edge Codebase

## Overview
This document provides essential guidance for AI coding agents working within the Kos Edge codebase. Understanding the architecture, workflows, and conventions is crucial for effective contributions.

## Architecture
- **Components**: The application is structured around a Next.js framework, with a clear separation of concerns across various directories such as `app`, `components`, and `lib`.
- **Service Boundaries**: The `model-service` directory contains the FastAPI backend, which handles data processing and API endpoints. The frontend communicates with this service for dynamic data.
- **Data Flow**: Data flows from the backend (FastAPI) to the frontend (Next.js) through API calls, particularly in files like `src/main.py` and `app/pro/[sport]/slate/[date]/page.tsx`.

## Developer Workflows
- **Running the Application**: Use `npm run dev` to start the development server. Ensure that the backend service is also running for full functionality.
- **Testing**: Implement tests in the `model-service` directory. Use pytest for Python tests and Jest for JavaScript tests.
- **Debugging**: Utilize console logs and the built-in debugging tools in VS Code. For backend issues, check FastAPI logs.

## Project-Specific Conventions
- **File Naming**: Follow camelCase for JavaScript/TypeScript files and snake_case for Python files. Directories should be lowercase.
- **Component Structure**: Each React component should be in its own file within the `components` directory. Use functional components and hooks where applicable.
- **Styling**: Tailwind CSS is used for styling. Classes should be applied directly in JSX elements.

## Integration Points
- **API Endpoints**: The backend exposes several endpoints, such as `/api/odds/snapshots` for fetching odds data. Refer to `src/main.py` for a complete list of available endpoints.
- **External Dependencies**: The project relies on several external libraries, including FastAPI, SQLAlchemy, and Next.js. Ensure all dependencies are listed in `requirements.txt` and `package.json`.

## Cross-Component Communication
- **Props and Context**: Use props for passing data between components. For global state management, consider using React Context or a state management library.
- **MDX Integration**: The `lib/mdx.ts` file handles MDX content. Use the `getMdxBySlug` function to fetch MDX content dynamically.

## Examples
- **Fetching Data**: In `app/pro/[sport]/slate/[date]/page.tsx`, data is fetched and displayed using a combination of API calls and React state management.
- **Component Usage**: The `Container` component in `components/Container.tsx` is used to wrap content with consistent styling across pages.

## Conclusion
This document serves as a foundational guide for AI agents to navigate and contribute effectively to the Kos Edge codebase. For further details, refer to specific files and components as needed.