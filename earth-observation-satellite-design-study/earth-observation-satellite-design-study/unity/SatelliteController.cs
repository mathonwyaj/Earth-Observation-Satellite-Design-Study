using System;
using System.IO;
using UnityEngine;

// Desktop prototype: attach to Satellite_Root, then assign the two panel fields.
// Reads Python outputs; does not perform or validate spacecraft sizing itself.
public class SatelliteController : MonoBehaviour
{
    public Transform leftPanel;
    public Transform rightPanel;
    public float rotationSpeed = 15f;

    [Serializable]
    public class Configuration
    {
        public string name;
        public float payload_mass_kg, payload_power_w, orbit_average_w;
        public float battery_capacity_wh, array_output_w, panel_area_m2;
        public float wet_mass_kg, mass_headroom_kg, simultaneous_load_w;
        public float panel_mass_kg, eps_mass_kg;
        public bool mass_target_pass;
    }

    [Serializable]
    public class DesignResults
    {
        public int schema_version;
        public Configuration[] configurations;
    }

    private DesignResults data;
    private int selected;
    private bool rotating;
    private string error;
    private Quaternion initialRotation;
    private Vector2 scrollPosition;
    private GUIStyle wrappedLabel;
    private string selectedPart;
    private Transform body;
    private Transform payload;
    private Camera viewCamera;
    private Rect originalViewport;

    private float InterfaceScale()
    {
        return Mathf.Max(0.1f, Mathf.Min(1.5f,
            Mathf.Min(Screen.width / 1280f, Screen.height / 800f)));
    }

    private void UpdateViewport()
    {
        if (viewCamera == null || Screen.width <= 0) return;
        float sidebarEdge = Mathf.Clamp(314f * InterfaceScale() / Screen.width, 0f, 0.65f);
        viewCamera.rect = new Rect(sidebarEdge, 0f, 1f - sidebarEdge, 1f);
    }

    private void OnDestroy()
    {
        if (viewCamera != null) viewCamera.rect = originalViewport;
    }

    private void Start()
    {
        initialRotation = transform.localRotation;
        viewCamera = Camera.main;
        if (viewCamera != null) originalViewport = viewCamera.rect;
        UpdateViewport();
        body = transform.Find("Satellite_Body");
        payload = transform.Find("Camera_Payload");
        try
        {
            if (leftPanel == null || rightPanel == null || leftPanel == rightPanel)
                throw new InvalidOperationException("Assign distinct Left Panel and Right Panel objects in the Inspector.");
            string path = Path.Combine(Application.streamingAssetsPath, "satellite_design_results.json");
            data = JsonUtility.FromJson<DesignResults>(File.ReadAllText(path));
            if (data == null || data.schema_version != 1 || data.configurations == null || data.configurations.Length == 0)
                throw new InvalidDataException("Expected schema_version 1 and at least one configuration.");
            foreach (Configuration item in data.configurations)
            {
                if (item == null || string.IsNullOrEmpty(item.name) ||
                    float.IsNaN(item.panel_area_m2) || float.IsInfinity(item.panel_area_m2) ||
                    item.panel_area_m2 <= 0f)
                    throw new InvalidDataException("A configuration is missing its name or valid panel area.");
            }
            ApplyConfiguration(0);
            Debug.Log("SatelliteController: loaded " + data.configurations.Length + " configurations.");
        }
        catch (Exception exception)
        {
            error = exception.Message;
            Debug.LogError("SatelliteController: " + error, this);
        }
    }

    private void ApplyConfiguration(int index)
    {
        selected = index;
        // Each cube is 1 unit wide before scaling. One Unity unit represents 1 m.
        // Keep the 0.65 m wing span fixed; vary its Z dimension to match face area.
        float depth = data.configurations[index].panel_area_m2 / (2f * 0.65f);
        foreach (Transform panel in new[] { leftPanel, rightPanel })
            panel.localScale = new Vector3(0.65f, 0.02f, depth);
        // Camera appearance stays illustrative: mass alone does not specify geometry.
    }

    private void Update()
    {
        UpdateViewport();
        if (rotating && error == null)
            transform.Rotate(Vector3.up, rotationSpeed * Time.deltaTime, Space.Self);
    }

    private void HandleSubsystemClick(float uiScale)
    {
        Event click = Event.current;
        if (error != null || data == null || click.type != EventType.MouseDown || click.button != 0)
            return;
        // Called before GUI.matrix changes: event coordinates are unscaled pixels.
        Rect sidebarPixels = new Rect(12 * uiScale, 12 * uiScale,
                                      290 * uiScale, Screen.height - 24 * uiScale);
        if (sidebarPixels.Contains(click.mousePosition) || Camera.main == null)
            return;
        Vector3 screenPoint = new Vector3(click.mousePosition.x,
                                         Screen.height - click.mousePosition.y, 0);
        // Ensure colliders follow the latest animated root/panel transforms.
        Physics.SyncTransforms();
        RaycastHit hit;
        if (Physics.Raycast(Camera.main.ScreenPointToRay(screenPoint), out hit,
                            Mathf.Infinity, Physics.DefaultRaycastLayers,
                            QueryTriggerInteraction.Ignore))
        {
            Transform part = hit.collider.transform;
            if (part == leftPanel || part.IsChildOf(leftPanel)) selectedPart = "Left solar panel";
            else if (part == rightPanel || part.IsChildOf(rightPanel)) selectedPart = "Right solar panel";
            else if (payload != null && (part == payload || part.IsChildOf(payload))) selectedPart = "Camera payload";
            else if (body != null && (part == body || part.IsChildOf(body))) selectedPart = "Satellite body";
            else selectedPart = null;
        }
        else selectedPart = null;
        // Do not Use() the event: GUILayout must receive matching layout passes.
    }

    private void DrawSubsystemInformation(Configuration item)
    {
        GUILayout.Space(10);
        GUILayout.Label("SUBSYSTEM INSPECTOR");
        if (selectedPart == null)
        {
            GUILayout.Label("Click the body, camera barrel or either solar panel in the 3D view.", wrappedLabel);
            return;
        }
        GUILayout.Label(selectedPart);
        if (selectedPart == "Camera payload")
        {
            GUILayout.Label("Captures Earth-observation imagery. Mass and operating power follow the selected configuration.", wrappedLabel);
            GUILayout.Label("Mass: " + item.payload_mass_kg.ToString("F1") + " kg");
            GUILayout.Label("Operating demand: " + item.payload_power_w.ToString("F1") + " W");
            GUILayout.Label("Off during eclipse in this study. Imaging quality has not been specified.", wrappedLabel);
        }
        else if (selectedPart == "Satellite body")
        {
            GUILayout.Label("Illustrative spacecraft bus: supports and houses avionics, attitude control, power equipment and other subsystems.", wrappedLabel);
            GUILayout.Label("Dimensions: 0.8 x 1.0 x 0.8 m. This shape does not establish packaging feasibility or represent a single subsystem mass.", wrappedLabel);
        }
        else
        {
            GUILayout.Label("Converts sunlight into electrical power for sunlight operations and battery recharge.", wrappedLabel);
            GUILayout.Label("This wing's face area: " + (item.panel_area_m2 / 2f).ToString("F3") + " m2");
            GUILayout.Label("This wing's estimated mass: " + (item.panel_mass_kg / 2f).ToString("F2") + " kg");
            GUILayout.Label("Combined array design output: " + item.array_output_w.ToString("F2") + " W");
            GUILayout.Label("Output assumes the illumination and performance factors in the Python model.", wrappedLabel);
        }
        if (GUILayout.Button("Clear selection")) selectedPart = null;
    }

    private void OnGUI()
    {
        // Reference-sized UI remains usable in a small Game view.
        float uiScale = InterfaceScale();
        HandleSubsystemClick(uiScale);
        Matrix4x4 oldMatrix = GUI.matrix;
        GUI.matrix = Matrix4x4.Scale(new Vector3(uiScale, uiScale, 1f));
        if (wrappedLabel == null)
            wrappedLabel = new GUIStyle(GUI.skin.label) { wordWrap = true };
        GUILayout.BeginArea(new Rect(12, 12, 290, Screen.height / uiScale - 24), GUI.skin.box);
        scrollPosition = GUILayout.BeginScrollView(scrollPosition);
        GUILayout.Label("SATELLITE DESIGN EXPLORER");
        GUILayout.Label("Illustrative preliminary sizing", wrappedLabel);
        GUILayout.Space(8);
        if (error != null)
        {
            GUILayout.Label("Setup error: " + error, wrappedLabel);
        }
        else if (data != null)
        {
            for (int i = 0; i < data.configurations.Length; i++)
                if (GUILayout.Button((i == selected ? "> " : "") + data.configurations[i].name,
                                     GUILayout.Height(32)))
                    ApplyConfiguration(i);
            Configuration item = data.configurations[selected];
            GUILayout.Space(10);
            GUILayout.Label("Payload mass: " + item.payload_mass_kg.ToString("F1") + " kg");
            GUILayout.Label("Payload power: " + item.payload_power_w.ToString("F1") + " W");
            GUILayout.Label("Orbit average: " + item.orbit_average_w.ToString("F2") + " W");
            GUILayout.Label("Battery capacity: " + item.battery_capacity_wh.ToString("F2") + " Wh");
            GUILayout.Label("Array output: " + item.array_output_w.ToString("F2") + " W");
            GUILayout.Label("Panel area: " + item.panel_area_m2.ToString("F3") + " m2");
            GUILayout.Label("Wet mass: " + item.wet_mass_kg.ToString("F2") + " kg");
            GUILayout.Label("Mass headroom: " + item.mass_headroom_kg.ToString("F2") + " kg");
            GUILayout.Label("Simultaneous load: " + item.simultaneous_load_w.ToString("F1") + " W");
            GUILayout.Label("Mass target: " + (item.mass_target_pass ? "PASS" : "FAIL"));
            GUILayout.Space(10);
            if (GUILayout.Button(rotating ? "Pause rotation" : "Rotate satellite", GUILayout.Height(30)))
                rotating = !rotating;
            if (GUILayout.Button("Reset orientation", GUILayout.Height(30)))
            {
                rotating = false;
                transform.localRotation = initialRotation;
            }
            DrawSubsystemInformation(item);
            GUILayout.Space(8);
            GUILayout.Label("Panel face area follows Python data. Body and camera geometry are illustrative. Rotation is for viewing, not an attitude simulation.", wrappedLabel);
            GUILayout.Label("Mass compliance alone does not confirm hardware feasibility.", wrappedLabel);
        }
        GUILayout.EndScrollView();
        GUILayout.EndArea();
        GUI.matrix = oldMatrix;
    }
}
