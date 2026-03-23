-- =============================================================================
-- AC Visualizer: 3ds Max → FBX Pipeline
-- Opens .max file (even without V-Ray/Corona), replaces missing materials
-- with Physical Material + original textures, exports FBX with embedded media.
--
-- When V-Ray/Corona DLLs are missing, 3ds Max loads the scene but replaces
-- renderer-specific materials with "Missing" placeholders. This script:
--   1. Reads the original bitmap paths from the .max file metadata
--   2. Creates Physical Materials with those bitmaps
--   3. Assigns them to the correct objects
--   4. Exports FBX with embedded textures
--
-- Usage: 3dsmaxbatch.exe "pipeline\max-to-fbx.ms" -v 4
-- =============================================================================

(
    -- ===================== CONFIGURATION =====================
    local inputFile = @"C:\Users\Jelinek\Documents\CLAUDE\ac_visualiser\models\samsung windfree\Samsung Windfree Split Air Conditioner Vray.max"
    local mapsDir = @"C:\Users\Jelinek\Documents\CLAUDE\ac_visualiser\models\samsung windfree\Maps\"
    local outputFile = @"C:\Users\Jelinek\Documents\CLAUDE\ac_visualiser\models\samsung windfree\output\windfree.fbx"

    -- ===================== OPEN SCENE =====================
    print "SCRIPT STARTED"
    format "\n========================================\n"
    format "AC Pipeline: Opening %\n" inputFile

    local outDir = getFilenamePath outputFile
    makeDir outDir all:true

    -- Open quietly (will show warnings about missing plugins but load geometry)
    loadMaxFile inputFile quiet:true

    if objects.count == 0 then (
        format "ERROR: Scene is empty!\n"
    ) else (
        format "Scene loaded: % objects\n" objects.count

        -- ===================== SCENE ANALYSIS =====================
        format "\n--- Geometry Objects ---\n"
        for o in geometry do (
            local bb = nodeGetBoundingBox o (matrix3 1)
            local sz = bb[2] - bb[1]
            local matClass = if o.material != undefined then (classof o.material) as string else "none"
            local matName = if o.material != undefined then o.material.name else "NO_MAT"
            format "  %-35s | mat: %-25s (%s)\n" o.name matName matClass
        )

        -- ===================== LIST ALL BITMAPS IN SCENE =====================
        format "\n--- Bitmaps in scene ---\n"
        local allBitmaps = getClassInstances BitmapTexture
        for bm in allBitmaps do (
            format "  [%] filename: %\n" bm.name bm.filename
        )

        -- ===================== CREATE PHYSICAL MATERIALS =====================
        format "\n--- Creating Physical Materials ---\n"

        -- Helper: create Physical Material with optional diffuse/alpha/bump/emissive
        fn makePBRMat matName diffuseColor:#(0.95, 0.95, 0.95) roughnessVal:0.3 metallicVal:0.0 \
                       diffuseMap:undefined alphaMap:undefined bumpMap:undefined emissiveMap:undefined = (
            local m = PhysicalMaterial()
            m.name = matName
            m.base_color = color (diffuseColor[1]*255) (diffuseColor[2]*255) (diffuseColor[3]*255)
            m.roughness = roughnessVal
            m.metalness = metallicVal

            if diffuseMap != undefined then (
                local bm = BitmapTexture()
                bm.filename = diffuseMap
                m.base_color_map = bm
                format "    + diffuse: %\n" diffuseMap
            )

            if alphaMap != undefined then (
                local bm = BitmapTexture()
                bm.filename = alphaMap
                m.cutout_map = bm
                format "    + alpha: %\n" alphaMap
            )

            if bumpMap != undefined then (
                local bm = BitmapTexture()
                bm.filename = bumpMap
                -- Use Normal Bump for Physical Material
                local nb = Normal_Bump()
                nb.normal_map = bm
                nb.mult_spin = 0.3
                m.bump_map = nb
                format "    + bump: %\n" bumpMap
            )

            if emissiveMap != undefined then (
                local bm = BitmapTexture()
                bm.filename = emissiveMap
                m.emission_color_map = bm
                m.emission = 2.0
                format "    + emissive: %\n" emissiveMap
            )

            m
        )

        -- Create materials based on known Samsung WindFree texture mapping
        -- Samsung Logo is black-bg with white text — used as mask in V-Ray, not diffuse
        -- We skip it here; logo is applied at runtime via canvas texture in Three.js
        format "  Body (white plastic, logo applied at runtime):\n"
        local matBody = makePBRMat "AC_Body" \
            diffuseColor:#(0.96, 0.96, 0.96) roughnessVal:0.25

        format "  Body Lower:\n"
        local matBodyLower = makePBRMat "AC_Body_Lower" \
            diffuseColor:#(0.94, 0.94, 0.94) roughnessVal:0.3

        format "  Fence/Net (WindFree mesh):\n"
        local matFence = makePBRMat "AC_WindFree_Mesh" \
            diffuseColor:#(1.0, 1.0, 1.0) roughnessVal:0.35 \
            alphaMap:(mapsDir + "Front Mesh Alpha.jpg") \
            bumpMap:(mapsDir + "Front Mesh Bump.jpg")

        format "  Display:\n"
        local matDisplay = makePBRMat "AC_Display" \
            diffuseColor:#(0.05, 0.05, 0.05) roughnessVal:0.4 metallicVal:0.1 \
            emissiveMap:(mapsDir + "Display Logo 01.jpg")

        format "  Swing:\n"
        local matSwing = makePBRMat "AC_Swing" \
            diffuseColor:#(0.94, 0.94, 0.94) roughnessVal:0.15

        format "  Inner:\n"
        local matInner = makePBRMat "AC_Inner" \
            diffuseColor:#(0.15, 0.15, 0.15) roughnessVal:0.6 metallicVal:0.1

        format "  Lock:\n"
        local matLock = makePBRMat "AC_Lock" \
            diffuseColor:#(0.55, 0.55, 0.55) roughnessVal:0.4 metallicVal:0.2

        -- ===================== ASSIGN MATERIALS =====================
        format "\n--- Assigning materials ---\n"
        for o in geometry do (
            local n = toLower o.name
            local mat = matBody  -- default

            if findString n "digital display" != undefined OR findString n "digital_display" != undefined then mat = matDisplay
            else if findString n "body_lower" != undefined OR findString n "body lower" != undefined then mat = matBodyLower
            else if findString n "ac_body" != undefined OR findString n "ac body" != undefined then mat = matBody
            else if findString n "fence" != undefined OR findString n "net" != undefined then mat = matFence
            else if findString n "swing_plate" != undefined OR findString n "swing plate" != undefined then mat = matSwing
            else if findString n "swing" != undefined then mat = matSwing
            else if findString n "innner" != undefined OR findString n "inner" != undefined then mat = matInner
            else if findString n "lower_machine" != undefined OR findString n "lower machine" != undefined then mat = matInner
            else if findString n "lock" != undefined then mat = matLock

            o.material = mat
            format "  %-35s -> %\n" o.name mat.name
        )

        -- ===================== EXPORT FBX =====================
        format "\n--- Exporting FBX ---\n"
        format "Output: %\n" outputFile

        FBXExporterSetParam "Animation" false
        FBXExporterSetParam "Cameras" false
        FBXExporterSetParam "Lights" false
        FBXExporterSetParam "EmbedTextures" true
        FBXExporterSetParam "FileVersion" "FBX202000"
        FBXExporterSetParam "ConvertUnit" "cm"
        FBXExporterSetParam "UpAxis" "Y"
        FBXExporterSetParam "SmoothingGroups" true
        FBXExporterSetParam "TangentSpaceExport" true
        FBXExporterSetParam "Preserveinstances" false
        FBXExporterSetParam "Triangulate" true

        exportFile outputFile #noPrompt selectedOnly:false using:FBXEXP

        -- Check if file exists
        if doesFileExist outputFile then (
            local fi = getFileSize outputFile
            format "\nSUCCESS: % (% bytes)\n" outputFile fi
        ) else (
            format "\nERROR: Export failed!\n"
        )

        format "========================================\n"
    )
)
