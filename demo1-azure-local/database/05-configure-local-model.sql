/* ============================================================================
   Caldova Regional Care Transfer Center
   05-configure-local-model.sql : enable REST calls and register Foundry Local
   ============================================================================ */

USE [master];
GO

EXEC sys.sp_configure N'external rest endpoint enabled', 1;
RECONFIGURE;
GO

USE [CaldovaRegionalCare];
GO

IF EXISTS (SELECT 1 FROM ai.ModelEndpoint WHERE EndpointName = N'FoundryLocalWindows')
   AND NOT EXISTS (SELECT 1 FROM ai.ModelEndpoint WHERE EndpointName = N'FoundryLocalOnAzureLocal')
BEGIN
    UPDATE ai.ModelEndpoint
    SET EndpointName = N'FoundryLocalOnAzureLocal'
    WHERE EndpointName = N'FoundryLocalWindows';
END;

IF EXISTS (SELECT 1 FROM ai.ModelEndpoint WHERE EndpointName = N'FoundryLocalOnAzureLocal')
BEGIN
    UPDATE ai.ModelEndpoint
    SET BaseUrl = N'https://localhost:8445',
        ModelId = N'Phi-3.5-mini-instruct-openvino-gpu',
        CredentialName = NULL,
        TimeoutSeconds = 180,
        IsActive = 1
    WHERE EndpointName = N'FoundryLocalOnAzureLocal';
END;
ELSE
BEGIN
    INSERT ai.ModelEndpoint
        (EndpointName, BaseUrl, ModelId, CredentialName, TimeoutSeconds, IsActive)
    VALUES
        (N'FoundryLocalOnAzureLocal', N'https://localhost:8445',
         N'Phi-3.5-mini-instruct-openvino-gpu', NULL, 180, 1);
END;
GO

SELECT EndpointName, BaseUrl, ModelId, TimeoutSeconds, IsActive
FROM ai.ModelEndpoint
WHERE EndpointName = N'FoundryLocalOnAzureLocal';
GO