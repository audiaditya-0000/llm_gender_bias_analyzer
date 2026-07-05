import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ScenarioManager from "./pages/ScenarioManager";
import ScaffoldManager from "./pages/ScaffoldManager";
import CounterfactualGenerator from "./pages/CounterfactualGenerator";
import ExperimentConfig from "./pages/ExperimentConfig";
import ExperimentRunner from "./pages/ExperimentRunner";
import ResponseViewer from "./pages/ResponseViewer";
import BlindCoding from "./pages/BlindCoding";
import AnalysisDashboard from "./pages/AnalysisDashboard";
import ExportPage from "./pages/ExportPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ScenarioManager />} />
          <Route path="scaffolds" element={<ScaffoldManager />} />
          <Route path="counterfactual" element={<CounterfactualGenerator />} />
          <Route path="experiments" element={<ExperimentConfig />} />
          <Route path="runner" element={<ExperimentRunner />} />
          <Route path="responses" element={<ResponseViewer />} />
          <Route path="coding" element={<BlindCoding />} />
          <Route path="analysis" element={<AnalysisDashboard />} />
          <Route path="export" element={<ExportPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
