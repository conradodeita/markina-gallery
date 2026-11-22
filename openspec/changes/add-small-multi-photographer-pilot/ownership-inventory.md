# Inventário de código — complemento da matriz

Gerado por `inventory_ownership.py`; consultar `ownership-matrix.md` para decisões, critérios A–X, testes e limites. Este inventário estático associa fontes a critérios; não executa testes nem decide prontidão. O estado e as evidências de implementação/validação estão na matriz e em `validation.md`.

SHA256 das fontes inventariadas: `2f0423b411775486b8c06801bdf291866187d2c602a7efd51078a1771e5e0b07`.

Contagens: arquivos=438; efeito potencial=643; estado=326; gate=734; produtor=245; query/ORM=5600; rotas=359; sitios=7215; tabelas=136.

## Tabelas

| Tabela/modelo | Classe | Critério/teste | Fonte | FKs atuais | Evidência por critério |
| --- | --- | --- | --- | --- | --- |
| `branding_settings` / `BrandingSettings` | R | K | `backend/app/auth.py:111` | tenant.id | ver matriz |
| `admin_user` / `AdminUser` | I | A | `backend/app/auth.py:154` | sem FK | ver matriz |
| `admin_totp_enrollment` / `AdminTotpEnrollment` | M | A | `backend/app/auth.py:189` | admin_user.id; tenant.id | ver matriz |
| `admin_totp_recovery_code` / `AdminTotpRecoveryCode` | I | A | `backend/app/auth.py:209` | admin_user.id | ver matriz |
| `installation_operator` / `InstallationOperator` | I | O | `backend/app/auth.py:280` | admin_user.id | ver matriz |
| `facial_embedding_experiment_setting` / `FacialEmbeddingExperimentSetting` | I | O | `backend/app/auth.py:295` | admin_user.id | ver matriz |
| `tenant` / `Tenant` | I | A | `backend/app/auth.py:321` | sem FK | ver matriz |
| `tenant_closure_request` / `TenantClosureRequest` | R | L | `backend/app/auth.py:348` | admin_user.id; tenant.id | ver matriz |
| `tenant_closure_recovery_batch` / `TenantClosureRecoveryBatch` | R | L | `backend/app/auth.py:386` | platform_owner.admin_user_id; tenant.id; composta:fk_closure_recovery_batch_closure | ver matriz |
| `tenant_closure_recovery_item` / `TenantClosureRecoveryItem` | D | L | `backend/app/auth.py:405` | tenant.id; composta:fk_closure_recovery_item_batch; composta:fk_closure_recovery_item_operation | ver matriz |
| `tenant_closure_media_deletion_batch` / `TenantClosureMediaDeletionBatch` | R | L | `backend/app/auth.py:423` | platform_owner.admin_user_id; tenant.id; composta:fk_closure_media_deletion_batch_closure | ver matriz |
| `tenant_closure_media_deletion_item` / `TenantClosureMediaDeletionItem` | D | L | `backend/app/auth.py:476` | tenant.id; composta:fk_closure_media_deletion_item_batch; composta:fk_closure_media_deletion_item_operation | ver matriz |
| `photographer_signup` / `PhotographerSignup` | I | A | `backend/app/auth.py:503` | tenant.id | ver matriz |
| `photographer_business_profile` / `PhotographerBusinessProfile` | R | A | `backend/app/auth.py:529` | admin_user.id; tenant.id | ver matriz |
| `photographer_terms_acceptance` / `PhotographerTermsAcceptance` | R | A | `backend/app/auth.py:556` | admin_user.id; tenant.id | ver matriz |
| `photographer_terms_draft` / `PhotographerTermsDraft` | I | A | `backend/app/auth.py:574` | admin_user.id | ver matriz |
| `photographer_terms_version` / `PhotographerTermsVersion` | I | A | `backend/app/auth.py:590` | admin_user.id | ver matriz |
| `google_drive_oauth_attempt` / `GoogleDriveOAuthAttempt` | M | A | `backend/app/auth.py:609` | admin_user.id; auth_session.id; tenant.id | ver matriz |
| `google_drive_connection` / `GoogleDriveConnection` | R | K | `backend/app/auth.py:623` | admin_user.id; tenant.id | ver matriz |
| `tenant_admin` / `TenantAdmin` | D | A | `backend/app/auth.py:642` | admin_user.id; tenant.id | ver matriz |
| `tenant_closure_identity_verification` / `TenantClosureIdentityVerification` | R | L | `backend/app/auth.py:652` | tenant.id; composta:fk_closure_identity_closure; composta:fk_closure_identity_membership | ver matriz |
| `admin_security_challenge` / `AdminSecurityChallenge` | M | A | `backend/app/auth.py:711` | admin_user.id; tenant.id | ver matriz |
| `admin_action_token` / `AdminActionToken` | I | A | `backend/app/auth.py:744` | admin_user.id | ver matriz |
| `photographer_access_recovery` / `PhotographerAccessRecovery` | M | A | `backend/app/auth.py:760` | admin_user.id; tenant.id; composta:fk_access_recovery_closure; composta:fk_access_recovery_target_membership | ver matriz |
| `email_delivery` / `EmailDelivery` | I | A | `backend/app/auth.py:810` | sem FK | ver matriz |
| `email_delivery_attempt` / `EmailDeliveryAttempt` | I | A | `backend/app/auth.py:843` | email_delivery.id | ver matriz |
| `client` / `Client` | R | C | `backend/app/auth.py:860` | tenant.id | ver matriz |
| `client_phone` / `ClientPhone` | D | C | `backend/app/auth.py:872` | client.id; tenant.id; composta:fk_client_phone_client_tenant | ver matriz |
| `client_deletion_receipt` / `ClientDeletionReceipt` | R | C | `backend/app/auth.py:910` | admin_user.id; tenant.id | ver matriz |
| `gallery_access` / `GalleryAccess` | R | G | `backend/app/auth.py:945` | client.id; derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `parent_gallery` / `ParentGallery` | R | G | `backend/app/auth.py:971` | photo_asset.id; progressive_pricing_preset.id; tenant.id | ver matriz |
| `parent_gallery_registration` / `ParentGalleryRegistration` | D | G | `backend/app/auth.py:1042` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `photo_asset` / `PhotoAsset` | R | G | `backend/app/auth.py:1058` | derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_photo_asset_folder_gallery; composta:fk_photo_asset_folder_scope; composta:fk_photo_asset_parent_tenant; composta:fk_photo_asset_private_tenant | ver matriz |
| `raw_development_settings` / `RawDevelopmentSettings` | R | P | `backend/app/auth.py:1105` | tenant.id | ver matriz |
| `raw_development_job` / `RawDevelopmentJob` | R | P | `backend/app/auth.py:1126` | tenant.id; composta:fk_raw_development_photo_tenant | ver matriz |
| `photo_folder` / `PhotoFolder` | D | G | `backend/app/auth.py:1162` | derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `gallery_client_state` / `GalleryClientState` | D | G | `backend/app/auth.py:1232` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `folder_client_grant` / `FolderClientGrant` | D | G | `backend/app/auth.py:1261` | tenant.id; composta:fk_folder_client_grant_client_state; composta:fk_folder_client_grant_folder_parent | ver matriz |
| `derived_gallery` / `DerivedGallery` | R | G | `backend/app/auth.py:1291` | client.id; parent_gallery.id; tenant.id; composta:fk_derived_gallery_parent_tenant | ver matriz |
| `derived_gallery_membership` / `DerivedGalleryMembership` | D | G | `backend/app/auth.py:1329` | admin_user.id; client.id; parent_gallery.id; tenant.id; composta:fk_membership_gallery_parent | ver matriz |
| `derived_gallery_photo` / `DerivedGalleryPhoto` | D | G | `backend/app/auth.py:1382` | derived_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `derived_gallery_photo_origin` / `DerivedGalleryPhotoOrigin` | D | G | `backend/app/auth.py:1408` | derived_gallery_photo.id; tenant.id | ver matriz |
| `photo_selection` / `PhotoSelection` | D | S | `backend/app/auth.py:1436` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_favorite` / `PhotoFavorite` | D | S | `backend/app/auth.py:1470` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_view` / `PhotoView` | D | S | `backend/app/auth.py:1503` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_comment` / `PhotoComment` | D | S | `backend/app/auth.py:1536` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `payment_group` / `PaymentGroup` | R | S | `backend/app/auth.py:1563` | client.id; tenant.id | ver matriz |
| `provider_payment` / `ProviderPayment` | R | S | `backend/app/auth.py:1591` | client.id; tenant.id | ver matriz |
| `provider_payment_attempt` / `ProviderPaymentAttempt` | D | S | `backend/app/auth.py:1631` | client.id; tenant.id; composta:fk_provider_attempt_payment_owner | ver matriz |
| `provider_payment_receipt` / `ProviderPaymentReceipt` | D | S | `backend/app/auth.py:1653` | client.id; tenant.id; composta:fk_provider_receipt_payment_owner | ver matriz |
| `provider_payment_correction` / `ProviderPaymentCorrection` | D | S | `backend/app/auth.py:1680` | admin_user.id; client.id; tenant.id; composta:fk_provider_correction_payment_owner | ver matriz |
| `mercadopago_account` / `MercadoPagoAccount` | R | K | `backend/app/auth.py:1705` | tenant.id | ver matriz |
| `payment_preferences` / `PaymentPreferences` | D | K | `backend/app/auth.py:1726` | mercadopago_account.id; tenant.id | ver matriz |
| `mercadopago_payment` / `MercadoPagoPayment` | R | S | `backend/app/auth.py:1743` | client.id; mercadopago_account.id; tenant.id | ver matriz |
| `mercadopago_webhook` / `MercadoPagoWebhook` | D | S | `backend/app/auth.py:1793` | mercadopago_account.id; tenant.id | ver matriz |
| `sale_order` / `SaleOrder` | R | S | `backend/app/auth.py:1817` | client.id; derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_sale_order_canonical_state; composta:fk_sale_order_mp_owner; composta:fk_sale_order_payment_group_owner; composta:fk_sale_order_provider_payment_owner | ver matriz |
| `sale_order_item` / `SaleOrderItem` | D | S | `backend/app/auth.py:1933` | photo_asset.id; sale_order.id; tenant.id | ver matriz |
| `removed_photo_movement` / `RemovedPhotoMovement` | R | S | `backend/app/auth.py:1956` | client.id; tenant.id | ver matriz |
| `asset_file_cleanup` / `AssetFileCleanup` | R | L | `backend/app/auth.py:1979` | tenant.id | ver matriz |
| `gallery_lifecycle_operation` / `GalleryLifecycleOperation` | R | L | `backend/app/auth.py:1995` | tenant.id | ver matriz |
| `media_archive_cycle` / `MediaArchiveCycle` | R | L | `backend/app/auth.py:2048` | tenant.id; composta:fk_media_archive_cycle_folder_tenant; composta:fk_media_archive_cycle_parent_tenant | ver matriz |
| `media_archive_operation` / `MediaArchiveOperation` | R | L | `backend/app/auth.py:2104` | tenant.id; composta:fk_media_archive_operation_cycle_tenant | ver matriz |
| `media_archive_recovery_pricing` / `MediaArchiveRecoveryPricing` | I | O | `backend/app/auth.py:2171` | platform_owner.admin_user_id | ver matriz |
| `media_archive_recovery_request` / `MediaArchiveRecoveryRequest` | R | L | `backend/app/auth.py:2194` | tenant.id; composta:fk_archive_recovery_closure_batch; composta:fk_media_archive_recovery_request_actor_membership; composta:fk_media_archive_recovery_request_actor_owner; composta:fk_media_archive_recovery_request_cycle_tenant; composta:fk_media_archive_recovery_request_operation_scope; composta:fk_media_archive_recovery_request_retry_operation_tenant | ver matriz |
| `media_archive_recovery_credit_reservation` / `MediaArchiveRecoveryCreditReservation` | D | S | `backend/app/auth.py:2276` | tenant.id; composta:fk_media_archive_recovery_credit_reservation_operation_tenant | ver matriz |
| `media_archive_object` / `MediaArchiveObject` | D | L | `backend/app/auth.py:2316` | tenant.id; composta:fk_media_archive_object_cycle_tenant | ver matriz |
| `media_archive_event` / `MediaArchiveEvent` | D | L | `backend/app/auth.py:2351` | tenant.id; composta:fk_media_archive_event_cycle_tenant; composta:fk_media_archive_event_operation_tenant | ver matriz |
| `media_archive_notice` / `MediaArchiveNotice` | D | N | `backend/app/auth.py:2383` | tenant.id; composta:fk_media_archive_notice_cycle_tenant | ver matriz |
| `media_archive_coordinator` / `MediaArchiveCoordinator` | I | O | `backend/app/auth.py:2420` | composta:fk_media_archive_coordinator_operation | ver matriz |
| `media_archive_space_reservation` / `MediaArchiveSpaceReservation` | D | L | `backend/app/auth.py:2444` | tenant.id; composta:fk_media_archive_space_reservation_operation_tenant | ver matriz |
| `gallery_access_capability` / `GalleryAccessCapability` | D | G | `backend/app/auth.py:2472` | client.id; derived_gallery.id; gallery_access_capability.id; parent_gallery.id; tenant.id | ver matriz |
| `commercial_history_media` / `CommercialHistoryMedia` | R | S | `backend/app/auth.py:2567` | sale_order_item.id; tenant.id | ver matriz |
| `price_rule` / `PriceRule` | D | K | `backend/app/auth.py:2694` | parent_gallery.id; tenant.id | ver matriz |
| `pix_checkout_settings` / `PixCheckoutSettings` | D | K | `backend/app/auth.py:2715` | parent_gallery.id; tenant.id | ver matriz |
| `global_pix_settings` / `GlobalPixSettings` | R | K | `backend/app/auth.py:2741` | admin_user.id; tenant.id | ver matriz |
| `payment_communication` / `PaymentCommunication` | D | S | `backend/app/auth.py:2770` | admin_user.id; client.id; sale_order.id; tenant.id; composta:fk_payment_communication_group_owner | ver matriz |
| `payment_confirmation_correction` / `PaymentConfirmationCorrection` | D | S | `backend/app/auth.py:2795` | admin_user.id; payment_communication.id; sale_order.id; tenant.id | ver matriz |
| `payment_message_template` / `PaymentMessageTemplate` | R | K | `backend/app/auth.py:2831` | tenant.id | ver matriz |
| `payment_notification_outbox` / `PaymentNotificationOutbox` | D | N | `backend/app/auth.py:2843` | payment_communication.id; tenant.id | ver matriz |
| `gallery_reopening_request` / `GalleryReopeningRequest` | D | S | `backend/app/auth.py:2869` | admin_user.id; client.id; derived_gallery.id; parent_gallery.id; photo_folder.id; tenant.id; composta:fk_gallery_reopening_canonical_state; composta:fk_gallery_reopening_derived_folder_scope; composta:fk_gallery_reopening_folder_scope | ver matriz |
| `gallery_reopening_notification_outbox` / `GalleryReopeningNotificationOutbox` | D | N | `backend/app/auth.py:2980` | gallery_reopening_request.id; tenant.id | ver matriz |
| `progressive_pricing_preset` / `ProgressivePricingPreset` | R | K | `backend/app/auth.py:3012` | tenant.id | ver matriz |
| `progressive_pricing_tier` / `ProgressivePricingTier` | D | K | `backend/app/auth.py:3033` | progressive_pricing_preset.id; tenant.id | ver matriz |
| `gallery_membership_notification_outbox` / `GalleryMembershipNotificationOutbox` | R | N | `backend/app/auth.py:3062` | client.id; derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `whatsapp_channel_settings` / `WhatsAppChannelSettings` | R | K | `backend/app/auth.py:3128` | tenant.id | ver matriz |
| `whatsapp_tenant_credential` / `WhatsAppTenantCredential` | R | K | `backend/app/auth.py:3152` | tenant.id | ver matriz |
| `whatsapp_delivery` / `WhatsAppDelivery` | R | N | `backend/app/auth.py:3169` | tenant.id | ver matriz |
| `whatsapp_delivery_attempt` / `WhatsAppDeliveryAttempt` | D | N | `backend/app/auth.py:3213` | tenant.id; whatsapp_delivery.id | ver matriz |
| `whatsapp_webhook_receipt` / `WhatsAppWebhookReceipt` | R | N | `backend/app/auth.py:3233` | tenant.id | ver matriz |
| `media_derivative` / `MediaDerivative` | D | P | `backend/app/auth.py:3246` | photo_asset.id; tenant.id | ver matriz |
| `media_job` / `MediaJob` | R | P | `backend/app/auth.py:3270` | photo_asset.id; tenant.id | ver matriz |
| `preview_adjustment_settings` / `PreviewAdjustmentSettings` | R | K | `backend/app/auth.py:3294` | tenant.id | ver matriz |
| `gallery_preview_settings` / `GalleryPreviewSettings` | D | K | `backend/app/auth.py:3313` | parent_gallery.id; tenant.id | ver matriz |
| `folder_processing_settings` / `FolderProcessingSettings` | D | K | `backend/app/auth.py:3335` | photo_folder.id; tenant.id | ver matriz |
| `preview_adjustment` / `PreviewAdjustment` | D | P | `backend/app/auth.py:3360` | photo_asset.id; tenant.id | ver matriz |
| `gallery_facial_policy` / `GalleryFacialPolicy` | D | F | `backend/app/auth.py:3386` | admin_user.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_rollout` / `FacialRollout` | D | F | `backend/app/auth.py:3431` | admin_user.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_calibration_approval` / `FacialCalibrationApproval` | R | F | `backend/app/auth.py:3500` | admin_user.id; tenant.id | ver matriz |
| `facial_rollout_operation` / `FacialRolloutOperation` | R | F | `backend/app/auth.py:3559` | admin_user.id; tenant.id | ver matriz |
| `facial_legal_representation` / `FacialLegalRepresentation` | D | F | `backend/app/auth.py:3603` | admin_user.id; client.id; parent_gallery.id; tenant.id | ver matriz |
| `photo_analysis` / `PhotoAnalysis` | D | F | `backend/app/auth.py:3662` | photo_asset.id; tenant.id | ver matriz |
| `photo_face_embedding` / `PhotoFaceEmbedding` | D | F | `backend/app/auth.py:3691` | derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_face_embedding_photo_parent | ver matriz |
| `facial_search_request` / `FacialSearchRequest` | R | F | `backend/app/auth.py:3770` | client.id; gallery_facial_policy.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_search_consent_proof` / `FacialSearchConsentProof` | D | F | `backend/app/auth.py:3859` | tenant.id | ver matriz |
| `facial_search_snapshot_item` / `FacialSearchSnapshotItem` | D | F | `backend/app/auth.py:3895` | tenant.id; composta:fk_facial_snapshot_photo_parent; composta:fk_facial_snapshot_search_scope | ver matriz |
| `facial_search_candidate` / `FacialSearchCandidate` | D | F | `backend/app/auth.py:3942` | tenant.id; composta:fk_facial_candidate_photo_parent; composta:fk_facial_candidate_search_scope | ver matriz |
| `facial_job` / `FacialJob` | R | F | `backend/app/auth.py:3987` | derived_gallery.id; facial_search_request.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `facial_search_notification_outbox` / `FacialSearchNotificationOutbox` | D | F | `backend/app/auth.py:4048` | tenant.id; composta:fk_facial_notification_search_scope | ver matriz |
| `auth_challenge` / `AuthChallenge` | M | A | `backend/app/auth.py:4103` | tenant.id | ver matriz |
| `notification_setting` / `NotificationSetting` | R | K | `backend/app/auth.py:4127` | tenant.id | ver matriz |
| `notification_milestone` / `NotificationMilestone` | D | N | `backend/app/auth.py:4145` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `push_subscription` / `PushSubscription` | R | N | `backend/app/auth.py:4163` | admin_user.id; auth_session.id; client.id; tenant.id | ver matriz |
| `notification_event` / `NotificationEvent` | R | N | `backend/app/auth.py:4198` | client.id; derived_gallery.id; parent_gallery.id; sale_order.id; tenant.id | ver matriz |
| `notification_delivery` / `NotificationDelivery` | D | N | `backend/app/auth.py:4227` | admin_user.id; client.id; notification_event.id; push_subscription.id; tenant.id | ver matriz |
| `private_upload_batch` / `PrivateUploadBatch` | D | G | `backend/app/auth.py:4272` | admin_user.id; derived_gallery.id; tenant.id; composta:fk_private_upload_batch_folder_parent_tenant; composta:fk_private_upload_batch_parent_tenant | ver matriz |
| `private_upload_batch_asset` / `PrivateUploadBatchAsset` | D | G | `backend/app/auth.py:4315` | photo_asset.id; private_upload_batch.id; tenant.id | ver matriz |
| `auth_session` / `AuthSession` | M | A | `backend/app/auth.py:4328` | admin_user.id; client.id; tenant.id | ver matriz |
| `audit_event` / `AuditEvent` | M | A | `backend/app/auth.py:4354` | tenant.id | ver matriz |
| `platform_admin_event` / `PlatformAdminEvent` | M | A | `backend/app/auth.py:4365` | admin_user.id; tenant.id | ver matriz |
| `tenant_credit_wallet` / `TenantCreditWallet` | R | S | `backend/app/auth.py:4415` | tenant.id | ver matriz |
| `photographer_credit_package` / `PhotographerCreditPackage` | I | O | `backend/app/auth.py:4436` | platform_owner.admin_user_id | ver matriz |
| `photo_credit_operation` / `PhotoCreditOperation` | R | S | `backend/app/auth.py:4472` | tenant.id; composta:fk_credit_operation_photo_tenant | ver matriz |
| `photographer_credit_entry` / `PhotographerCreditEntry` | R | S | `backend/app/auth.py:4516` | admin_user.id; photographer_credit_package.id; platform_owner.admin_user_id; tenant.id; composta:fk_credit_entry_archive_operation_tenant; composta:fk_credit_entry_operation_tenant; composta:fk_credit_entry_source_tenant | ver matriz |
| `mercadopago_credit_purchase` / `MercadoPagoCreditPurchase` | M | S | `backend/app/auth.py:4608` | photographer_credit_package.id; platform_owner.admin_user_id; tenant.id; composta:fk_credit_purchase_buyer_membership; composta:fk_credit_purchase_ledger_tenant; composta:fk_credit_purchase_receiver_account_tenant | ver matriz |
| `mercadopago_credit_purchase_event` / `MercadoPagoCreditPurchaseEvent` | D | S | `backend/app/auth.py:4712` | tenant.id; composta:fk_credit_purchase_event_scope | ver matriz |
| `photographer_credit_allocation_event` / `PhotographerCreditAllocationEvent` | D | S | `backend/app/auth.py:4745` | tenant.id; composta:fk_credit_allocation_entry_tenant; composta:fk_credit_allocation_operation_tenant; composta:fk_credit_allocation_source_tenant | ver matriz |
| `media_archive_recovery_credit_allocation_event` / `MediaArchiveRecoveryCreditAllocationEvent` | D | S | `backend/app/auth.py:4794` | tenant.id; composta:fk_media_archive_credit_allocation_entry_tenant; composta:fk_media_archive_credit_allocation_operation_tenant; composta:fk_media_archive_credit_allocation_source_tenant | ver matriz |
| `photo_credit_operation_event` / `PhotoCreditOperationEvent` | D | S | `backend/app/auth.py:4852` | admin_user.id; tenant.id; composta:fk_credit_operation_event_scope | ver matriz |
| `platform_owner` / `PlatformOwner` | I | O | `backend/app/system_monitor/models.py:13` | admin_user.id | ver matriz |
| `system_monitor_grant` / `MonitorGrant` | I | O | `backend/app/system_monitor/models.py:23` | admin_user.id | ver matriz |
| `system_monitor_bucket` / `MonitorBucket` | I | O | `backend/app/system_monitor/models.py:33` | sem FK | ver matriz |
| `system_monitor_sample` / `MonitorSample` | I | O | `backend/app/system_monitor/models.py:45` | sem FK | ver matriz |
| `system_monitor_worker` / `MonitorWorker` | I | O | `backend/app/system_monitor/models.py:51` | sem FK | ver matriz |
| `system_monitor_activity` / `MonitorActivity` | I | O | `backend/app/system_monitor/models.py:59` | auth_session.id | ver matriz |
| `system_monitor_incident` / `MonitorIncident` | I | O | `backend/app/system_monitor/models.py:67` | sem FK | ver matriz |
| `system_monitor_transition` / `MonitorTransition` | I | O | `backend/app/system_monitor/models.py:76` | sem FK | ver matriz |

## Arquivos e fronteiras

| Arquivo | Critério/teste | Evidência por critério |
| --- | --- | --- |
| `backend/app/__init__.py` | I | ver matriz |
| `backend/app/acervo_context.py` | G | ver matriz |
| `backend/app/admin_account.py` | A | ver matriz |
| `backend/app/admin_security.py` | A | ver matriz |
| `backend/app/app_env_transition.py` | K | ver matriz |
| `backend/app/asset_removal.py` | L | ver matriz |
| `backend/app/auth.py` | A | ver matriz |
| `backend/app/branding_context.py` | K | ver matriz |
| `backend/app/canonical_selection.py` | S | ver matriz |
| `backend/app/capacity_observability/budget.py` | O | ver matriz |
| `backend/app/capacity_observability/collector.py` | O | ver matriz |
| `backend/app/capacity_observability/contracts.py` | O | ver matriz |
| `backend/app/capacity_observability/database.py` | O | ver matriz |
| `backend/app/capacity_observability/pool.py` | O | ver matriz |
| `backend/app/capacity_observability/queues.py` | O | ver matriz |
| `backend/app/checkout.py` | S | ver matriz |
| `backend/app/client_commerce.py` | S | ver matriz |
| `backend/app/client_identity.py` | C | ver matriz |
| `backend/app/client_lifecycle.py` | L | ver matriz |
| `backend/app/combined_environment_transition.py` | X | ver matriz |
| `backend/app/commercial_history.py` | S | ver matriz |
| `backend/app/commercial_projection.py` | S | ver matriz |
| `backend/app/commercial_removal.py` | L | ver matriz |
| `backend/app/commercial_retention.py` | L | ver matriz |
| `backend/app/credit_history.py` | S | ver matriz |
| `backend/app/email_delivery.py` | N | ver matriz |
| `backend/app/environment_transition_bundle.py` | X | ver matriz |
| `backend/app/environment_transition_channels.py` | N | ver matriz |
| `backend/app/environment_transition_inventory.py` | X | ver matriz |
| `backend/app/environment_transition_runtime.py` | X | ver matriz |
| `backend/app/facial/__init__.py` | F | ver matriz |
| `backend/app/facial/analysis_metrics.py` | F | ver matriz |
| `backend/app/facial/calibration.py` | F | ver matriz |
| `backend/app/facial/capacity.py` | F | ver matriz |
| `backend/app/facial/closure_cleanup.py` | F | ver matriz |
| `backend/app/facial/closure_gate.py` | F | ver matriz |
| `backend/app/facial/config.py` | F | ver matriz |
| `backend/app/facial/crypto.py` | F | ver matriz |
| `backend/app/facial/detection.py` | F | ver matriz |
| `backend/app/facial/engine.py` | F | ver matriz |
| `backend/app/facial/environment_backup.py` | F | ver matriz |
| `backend/app/facial/environment_eligibility.py` | F | ver matriz |
| `backend/app/facial/environment_migration.py` | F | ver matriz |
| `backend/app/facial/environment_migration_guard.py` | F | ver matriz |
| `backend/app/facial/environment_origin.py` | F | ver matriz |
| `backend/app/facial/environment_package_store.py` | F | ver matriz |
| `backend/app/facial/environment_sql.py` | F | ver matriz |
| `backend/app/facial/environment_sql_backup.py` | F | ver matriz |
| `backend/app/facial/face_worker.py` | F | ver matriz |
| `backend/app/facial/index_worker_entrypoint.py` | F | ver matriz |
| `backend/app/facial/indexing.py` | F | ver matriz |
| `backend/app/facial/jobs.py` | F | ver matriz |
| `backend/app/facial/lifecycle.py` | F | ver matriz |
| `backend/app/facial/maintenance_worker_entrypoint.py` | F | ver matriz |
| `backend/app/facial/manage_rollout.py` | F | ver matriz |
| `backend/app/facial/model_assets.py` | F | ver matriz |
| `backend/app/facial/notifications.py` | F | ver matriz |
| `backend/app/facial/observability.py` | F | ver matriz |
| `backend/app/facial/policy.py` | F | ver matriz |
| `backend/app/facial/provider.py` | F | ver matriz |
| `backend/app/facial/purge.py` | F | ver matriz |
| `backend/app/facial/quality.py` | F | ver matriz |
| `backend/app/facial/reconcile_gallery.py` | F | ver matriz |
| `backend/app/facial/reference.py` | F | ver matriz |
| `backend/app/facial/reference_store.py` | F | ver matriz |
| `backend/app/facial/regions.py` | F | ver matriz |
| `backend/app/facial/representation.py` | F | ver matriz |
| `backend/app/facial/retention.py` | F | ver matriz |
| `backend/app/facial/rollout.py` | F | ver matriz |
| `backend/app/facial/rollout_operation.py` | F | ver matriz |
| `backend/app/facial/runtime.py` | F | ver matriz |
| `backend/app/facial/search.py` | F | ver matriz |
| `backend/app/facial/search_worker.py` | F | ver matriz |
| `backend/app/facial/search_worker_entrypoint.py` | F | ver matriz |
| `backend/app/facial/security.py` | F | ver matriz |
| `backend/app/facial/serving.py` | F | ver matriz |
| `backend/app/facial/status.py` | F | ver matriz |
| `backend/app/facial/worker.py` | F | ver matriz |
| `backend/app/folder_access.py` | G | ver matriz |
| `backend/app/folder_deadlines.py` | G | ver matriz |
| `backend/app/folder_processing.py` | P | ver matriz |
| `backend/app/folder_processing_api.py` | P | ver matriz |
| `backend/app/gallery_access.py` | G | ver matriz |
| `backend/app/gallery_cleanup.py` | L | ver matriz |
| `backend/app/gallery_cover_readiness.py` | G | ver matriz |
| `backend/app/gallery_lifecycle.py` | L | ver matriz |
| `backend/app/gallery_pricing.py` | K | ver matriz |
| `backend/app/gallery_visuals.py` | G | ver matriz |
| `backend/app/global_pix.py` | K | ver matriz |
| `backend/app/google_drive_client.py` | O | ver matriz |
| `backend/app/google_drive_oauth.py` | A | ver matriz |
| `backend/app/google_drive_storage.py` | O | ver matriz |
| `backend/app/historical_media.py` | X | ver matriz |
| `backend/app/homolog_cleanup.py` | L | ver matriz |
| `backend/app/installation_operator.py` | O | ver matriz |
| `backend/app/integration_secrets.py` | X | ver matriz |
| `backend/app/main.py` | X | ver matriz |
| `backend/app/media.py` | P | ver matriz |
| `backend/app/media_archive_billing.py` | S | ver matriz |
| `backend/app/media_archive_executor.py` | L | ver matriz |
| `backend/app/media_archive_guards.py` | L | ver matriz |
| `backend/app/media_archive_manifest.py` | L | ver matriz |
| `backend/app/media_archive_notices.py` | L | ver matriz |
| `backend/app/media_archive_scheduler.py` | L | ver matriz |
| `backend/app/media_archive_staging.py` | L | ver matriz |
| `backend/app/media_archive_storage.py` | L | ver matriz |
| `backend/app/media_archive_worker.py` | L | ver matriz |
| `backend/app/membership_notifications.py` | N | ver matriz |
| `backend/app/mercadopago_api.py` | S | ver matriz |
| `backend/app/mercadopago_checkout.py` | S | ver matriz |
| `backend/app/mercadopago_credit_purchases.py` | S | ver matriz |
| `backend/app/mercadopago_projection.py` | S | ver matriz |
| `backend/app/mercadopago_provider.py` | S | ver matriz |
| `backend/app/mercadopago_settings.py` | K | ver matriz |
| `backend/app/mercadopago_webhook.py` | S | ver matriz |
| `backend/app/messaging.py` | N | ver matriz |
| `backend/app/notification_contract.py` | N | ver matriz |
| `backend/app/notification_delivery.py` | N | ver matriz |
| `backend/app/notification_events.py` | N | ver matriz |
| `backend/app/notification_settings.py` | K | ver matriz |
| `backend/app/order_delivery.py` | S | ver matriz |
| `backend/app/order_visibility.py` | S | ver matriz |
| `backend/app/ownership_schema.py` | X | ver matriz |
| `backend/app/parent_registration.py` | G | ver matriz |
| `backend/app/payment_availability.py` | K | ver matriz |
| `backend/app/payment_export.py` | S | ver matriz |
| `backend/app/payment_templates.py` | K | ver matriz |
| `backend/app/photographer_access_recovery.py` | A | ver matriz |
| `backend/app/photographer_cpf.py` | A | ver matriz |
| `backend/app/photographer_credits.py` | S | ver matriz |
| `backend/app/photographer_onboarding.py` | A | ver matriz |
| `backend/app/photographer_signup.py` | A | ver matriz |
| `backend/app/photographer_subdomain.py` | X | ver matriz |
| `backend/app/photographer_terms.py` | A | ver matriz |
| `backend/app/photographer_totp.py` | A | ver matriz |
| `backend/app/photographer_totp_support.py` | A | ver matriz |
| `backend/app/photographer_turnstile.py` | A | ver matriz |
| `backend/app/pix.py` | S | ver matriz |
| `backend/app/platform_backup/__init__.py` | O | ver matriz |
| `backend/app/platform_backup/archive.py` | O | ver matriz |
| `backend/app/platform_backup/catalog.py` | O | ver matriz |
| `backend/app/platform_backup/filesystem.py` | O | ver matriz |
| `backend/app/platform_backup/payload.py` | O | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py` | O | ver matriz |
| `backend/app/platform_backup/remote_copy.py` | O | ver matriz |
| `backend/app/platform_backup/restore.py` | O | ver matriz |
| `backend/app/platform_backup/retention.py` | O | ver matriz |
| `backend/app/platform_backup/storage.py` | O | ver matriz |
| `backend/app/platform_backup/worker.py` | O | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py` | O | ver matriz |
| `backend/app/platform_backup/workspace_store.py` | O | ver matriz |
| `backend/app/platform_console.py` | A | ver matriz |
| `backend/app/preview_adjustment/__init__.py` | P | ver matriz |
| `backend/app/preview_adjustment/api.py` | P | ver matriz |
| `backend/app/preview_adjustment/cleanup.py` | P | ver matriz |
| `backend/app/preview_adjustment/engine.py` | P | ver matriz |
| `backend/app/preview_adjustment/service.py` | P | ver matriz |
| `backend/app/preview_adjustment/worker.py` | P | ver matriz |
| `backend/app/pricing.py` | S | ver matriz |
| `backend/app/private_derivation.py` | G | ver matriz |
| `backend/app/private_fields.py` | A | ver matriz |
| `backend/app/private_folder_overview.py` | G | ver matriz |
| `backend/app/private_gallery_lifecycle.py` | L | ver matriz |
| `backend/app/private_membership.py` | G | ver matriz |
| `backend/app/private_upload_batches.py` | G | ver matriz |
| `backend/app/product_brand.py` | I | ver matriz |
| `backend/app/provision_installation_operator.py` | O | ver matriz |
| `backend/app/provision_photographer.py` | A | ver matriz |
| `backend/app/public_gallery_access.py` | G | ver matriz |
| `backend/app/public_origin.py` | I | ver matriz |
| `backend/app/push_subscriptions.py` | N | ver matriz |
| `backend/app/rotate_totp_keys.py` | A | ver matriz |
| `backend/app/schema_revision_check.py` | I | ver matriz |
| `backend/app/seed_admin.py` | A | ver matriz |
| `backend/app/statistics_report.py` | O | ver matriz |
| `backend/app/storage_metrics.py` | X | ver matriz |
| `backend/app/system_monitor/__init__.py` | O | ver matriz |
| `backend/app/system_monitor/access.py` | O | ver matriz |
| `backend/app/system_monitor/activity.py` | O | ver matriz |
| `backend/app/system_monitor/config.py` | O | ver matriz |
| `backend/app/system_monitor/grants.py` | O | ver matriz |
| `backend/app/system_monitor/host.py` | O | ver matriz |
| `backend/app/system_monitor/host_collect.py` | O | ver matriz |
| `backend/app/system_monitor/incidents.py` | O | ver matriz |
| `backend/app/system_monitor/models.py` | O | ver matriz |
| `backend/app/system_monitor/pool.py` | O | ver matriz |
| `backend/app/system_monitor/report.py` | O | ver matriz |
| `backend/app/system_monitor/routes.py` | O | ver matriz |
| `backend/app/system_monitor/runtime.py` | O | ver matriz |
| `backend/app/system_monitor/sanitize.py` | O | ver matriz |
| `backend/app/system_monitor/sources.py` | O | ver matriz |
| `backend/app/system_monitor/storage.py` | O | ver matriz |
| `backend/app/system_monitor/store.py` | O | ver matriz |
| `backend/app/system_monitor/telemetry.py` | O | ver matriz |
| `backend/app/tenancy.py` | A | ver matriz |
| `backend/app/tenant_closure.py` | L | ver matriz |
| `backend/app/tenant_closure_api.py` | L | ver matriz |
| `backend/app/tenant_closure_identity.py` | L | ver matriz |
| `backend/app/tenant_closure_obligations.py` | L | ver matriz |
| `backend/app/tenant_closure_recovery.py` | L | ver matriz |
| `backend/app/tenant_hosts.py` | X | ver matriz |
| `backend/app/tenant_media_deletion.py` | L | ver matriz |
| `backend/app/tenant_profile_retention.py` | L | ver matriz |
| `backend/app/totp_crypto.py` | A | ver matriz |
| `backend/app/totp_migration.py` | A | ver matriz |
| `backend/app/totp_recovery.py` | A | ver matriz |
| `backend/app/totp_verification.py` | A | ver matriz |
| `backend/app/unified_checkout.py` | S | ver matriz |
| `backend/app/web_push.py` | N | ver matriz |
| `backend/app/whatsapp_binding.py` | N | ver matriz |
| `backend/app/whatsapp_channel.py` | N | ver matriz |
| `backend/app/whatsapp_delivery.py` | N | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py` | N | ver matriz |
| `backend/app/whatsapp_webhook.py` | N | ver matriz |
| `backend/app/worker.py` | X | ver matriz |
| `scripts/__init__.py` | T | ver matriz |
| `scripts/app_env_transition_inventory.py` | T | ver matriz |
| `scripts/app_env_transition_inventory_report.py` | T | ver matriz |
| `scripts/assert_homolog_schema_head.py` | T | ver matriz |
| `scripts/backend_ci.py` | T | ver matriz |
| `scripts/build_python_security_candidates.py` | T | ver matriz |
| `scripts/check_ci_results.py` | T | ver matriz |
| `scripts/check_infinitepay_retirement_scope.py` | T | ver matriz |
| `scripts/check_preview_adjustment_migration_scope.py` | T | ver matriz |
| `scripts/check_prod_app_release_scope.py` | T | ver matriz |
| `scripts/check_prod_facial_release_gates.py` | T | ver matriz |
| `scripts/classify_ci_scope.py` | T | ver matriz |
| `scripts/classify_prod_release.py` | T | ver matriz |
| `scripts/dependency_release.py` | T | ver matriz |
| `scripts/deploy-homolog.sh` | T | ver matriz |
| `scripts/deploy-prod-app-services.sh` | T | ver matriz |
| `scripts/deploy-prod-facial-services.sh` | T | ver matriz |
| `scripts/deploy-prod-infinitepay-retirement.sh` | T | ver matriz |
| `scripts/deploy-prod-lock.sh` | T | ver matriz |
| `scripts/deploy-prod-nginx-provenance.sh` | T | ver matriz |
| `scripts/deploy-prod-preview-adjustment-migration.sh` | T | ver matriz |
| `scripts/deploy-prod-state.sh` | T | ver matriz |
| `scripts/deploy-prod-web.sh` | T | ver matriz |
| `scripts/environment_cutover_release.py` | T | ver matriz |
| `scripts/face_benchmark.py` | T | ver matriz |
| `scripts/face_spike/__init__.py` | T | ver matriz |
| `scripts/face_spike/arm_smoke.py` | T | ver matriz |
| `scripts/face_spike/dataset.py` | T | ver matriz |
| `scripts/face_spike/harness.py` | T | ver matriz |
| `scripts/face_spike/models.py` | T | ver matriz |
| `scripts/facial_runtime_candidate.py` | T | ver matriz |
| `scripts/facial_runtime_image_import.py` | T | ver matriz |
| `scripts/facial_runtime_layer_probe.py` | T | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py` | T | ver matriz |
| `scripts/facial_runtime_restoration.py` | T | ver matriz |
| `scripts/facial_runtime_restoration_cli.py` | T | ver matriz |
| `scripts/facial_runtime_restoration_host.py` | T | ver matriz |
| `scripts/install-prod-preview-migration-wrapper.sh` | T | ver matriz |
| `scripts/inventory-dependency-runtimes.py` | T | ver matriz |
| `scripts/inventory-homolog-readonly.sh` | T | ver matriz |
| `scripts/local_photographer_demo.py` | T | ver matriz |
| `scripts/local_tenant_closure_demo.py` | T | ver matriz |
| `scripts/maintain-homolog-data.sh` | T | ver matriz |
| `scripts/nginx_compose_provenance.py` | T | ver matriz |
| `scripts/operate-facial-rollout-homolog.sh` | T | ver matriz |
| `scripts/orders_pilot_release.py` | T | ver matriz |
| `scripts/prepare_emergency_api_image.py` | T | ver matriz |
| `scripts/preserve_branding.py` | T | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py` | T | ver matriz |
| `scripts/preview_adjustment_migration_release.py` | T | ver matriz |
| `scripts/preview_adjustment_migration_release_flow.py` | T | ver matriz |
| `scripts/preview_adjustment_smoke.py` | T | ver matriz |
| `scripts/preview_worker_maintenance_flow.py` | T | ver matriz |
| `scripts/preview_worker_security_inventory.py` | T | ver matriz |
| `scripts/preview_worker_security_journal.py` | T | ver matriz |
| `scripts/preview_worker_security_release.py` | T | ver matriz |
| `scripts/preview_worker_security_release_host.py` | T | ver matriz |
| `scripts/production-preflight-ssh-wrapper.sh` | T | ver matriz |
| `scripts/prove_preview_compose_preservation.py` | T | ver matriz |
| `scripts/python_security_release.py` | T | ver matriz |
| `scripts/reset-homolog-owner.sh` | T | ver matriz |
| `scripts/reset_homolog_owner.py` | T | ver matriz |
| `scripts/resume-homolog.sh` | T | ver matriz |
| `scripts/retirement_binding_removal.py` | T | ver matriz |
| `scripts/retirement_financial_evidence.py` | T | ver matriz |
| `scripts/retirement_host_references.py` | T | ver matriz |
| `scripts/retirement_inventory_policy.py` | T | ver matriz |
| `scripts/retirement_pix_evidence.py` | T | ver matriz |
| `scripts/specialized_pillow_candidate.py` | T | ver matriz |
| `scripts/specialized_pillow_probe.py` | T | ver matriz |
| `scripts/specialized_pillow_release.py` | T | ver matriz |
| `scripts/third_party_report.py` | T | ver matriz |
| `scripts/validate-homolog-public-origin.py` | T | ver matriz |
| `scripts/validate_retirement_approval.py` | T | ver matriz |
| `scripts/verify_main_ci_evidence.py` | T | ver matriz |
| `scripts/wildcard_certificate_custody.py` | T | ver matriz |
| `scripts/wildcard_npm_lab.py` | T | ver matriz |
| `scripts/wildcard_operational_bundle.py` | T | ver matriz |
| `scripts/wildcard_operational_custody.py` | T | ver matriz |
| `scripts/wildcard_operational_files.py` | T | ver matriz |
| `scripts/wildcard_operational_gateway.py` | T | ver matriz |
| `scripts/wildcard_operational_helper_lab.py` | T | ver matriz |
| `scripts/wildcard_operational_installer.py` | T | ver matriz |
| `scripts/wildcard_operational_issuer.py` | T | ver matriz |
| `scripts/wildcard_operational_npm_helper.py` | T | ver matriz |
| `scripts/wildcard_operational_npm_lab.py` | T | ver matriz |
| `scripts/wildcard_operational_package_manifest.py` | T | ver matriz |
| `scripts/wildcard_operational_protocol.py` | T | ver matriz |
| `scripts/wildcard_operational_runtime.py` | T | ver matriz |
| `scripts/wildcard_operational_service.py` | T | ver matriz |
| `scripts/wildcard_systemd_guest.py` | T | ver matriz |
| `scripts/wildcard_systemd_vm.py` | T | ver matriz |
| `frontend/app/(public)/admin/account-action.tsx` | U | ver matriz |
| `frontend/app/(public)/admin/reset-password/page.tsx` | U | ver matriz |
| `frontend/app/(public)/admin/verify-email/page.tsx` | U | ver matriz |
| `frontend/app/(public)/photographer-access-recovery/page.tsx` | U | ver matriz |
| `frontend/app/admin/admin-navigation.tsx` | U | ver matriz |
| `frontend/app/admin/capacity-diagnostics.tsx` | U | ver matriz |
| `frontend/app/admin/capacity-report.ts` | U | ver matriz |
| `frontend/app/admin/clients/client-controls.tsx` | U | ver matriz |
| `frontend/app/admin/clients/client-directory.tsx` | U | ver matriz |
| `frontend/app/admin/clients/page.tsx` | U | ver matriz |
| `frontend/app/admin/credits/credit-history.tsx` | U | ver matriz |
| `frontend/app/admin/credits/credit-purchase-checkout.tsx` | U | ver matriz |
| `frontend/app/admin/credits/credit-shortfall-notice.tsx` | U | ver matriz |
| `frontend/app/admin/credits/credit-upload-status.tsx` | U | ver matriz |
| `frontend/app/admin/credits/media-archive-recovery-panel.tsx` | U | ver matriz |
| `frontend/app/admin/credits/owner-credit-operations.tsx` | U | ver matriz |
| `frontend/app/admin/credits/owner-media-archive-recoveries.tsx` | U | ver matriz |
| `frontend/app/admin/credits/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/[galleryId]/orders/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/[galleryId]/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/[galleryId]/pricing/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/admin-photo-preview-dialog.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/client-gallery-card.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/folder-deadline-fields.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/folder-processing-panel.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/folder-upload-progress.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/new/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/pricing-rules.ts` | U | ver matriz |
| `frontend/app/admin/galleries/private-folder-client-overview.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/[step]/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/preview/page.tsx` | U | ver matriz |
| `frontend/app/admin/installation-diagnostics.tsx` | U | ver matriz |
| `frontend/app/admin/layout.tsx` | U | ver matriz |
| `frontend/app/admin/notifications/media-archive-notice-center.tsx` | U | ver matriz |
| `frontend/app/admin/notifications/page.tsx` | U | ver matriz |
| `frontend/app/admin/onboarding-gate-notice.tsx` | U | ver matriz |
| `frontend/app/admin/operations/page.tsx` | U | ver matriz |
| `frontend/app/admin/page.tsx` | U | ver matriz |
| `frontend/app/admin/payments/order-delivery.tsx` | U | ver matriz |
| `frontend/app/admin/payments/order-photos.tsx` | U | ver matriz |
| `frontend/app/admin/payments/page.tsx` | U | ver matriz |
| `frontend/app/admin/payments/payment-actions.tsx` | U | ver matriz |
| `frontend/app/admin/payments/removed-history.tsx` | U | ver matriz |
| `frontend/app/admin/platform/console-link.tsx` | U | ver matriz |
| `frontend/app/admin/platform/page.tsx` | U | ver matriz |
| `frontend/app/admin/platform/photographer-access-recovery.tsx` | U | ver matriz |
| `frontend/app/admin/platform/photographer-terms-editor.tsx` | U | ver matriz |
| `frontend/app/admin/platform/photographer-terms-history.tsx` | U | ver matriz |
| `frontend/app/admin/platform/photographer-totp-support.tsx` | U | ver matriz |
| `frontend/app/admin/platform/tenant-closure-console.tsx` | U | ver matriz |
| `frontend/app/admin/platform/use-console-access.ts` | U | ver matriz |
| `frontend/app/admin/previews/page.tsx` | U | ver matriz |
| `frontend/app/admin/pricing/page.tsx` | U | ver matriz |
| `frontend/app/admin/purchased-photo-export.ts` | U | ver matriz |
| `frontend/app/admin/purchases/page.tsx` | U | ver matriz |
| `frontend/app/admin/settings/onboarding-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/page.tsx` | U | ver matriz |
| `frontend/app/admin/settings/payment-providers-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/photographer-totp-setup.tsx` | U | ver matriz |
| `frontend/app/admin/settings/pix-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/security-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/tenant-address-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/tenant-closure-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/whatsapp-panel.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/monitor-hint.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/monitor-link.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/page.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/request.ts` | U | ver matriz |
| `frontend/app/admin/system-monitor/types.ts` | U | ver matriz |
| `frontend/app/admin/system-monitor/use-permissions.ts` | U | ver matriz |
| `frontend/app/admin/system-monitor/user-tree.tsx` | U | ver matriz |
| `frontend/app/admin/tenant-address-notice.tsx` | U | ver matriz |
| `frontend/app/admin/tenant-address.ts` | U | ver matriz |
| `frontend/app/admin-session-toolbar.tsx` | U | ver matriz |
| `frontend/app/api/health/route.ts` | U | ver matriz |
| `frontend/app/auth-entry.tsx` | U | ver matriz |
| `frontend/app/authenticated-identity.tsx` | U | ver matriz |
| `frontend/app/brand-logo.tsx` | U | ver matriz |
| `frontend/app/client-cart.tsx` | U | ver matriz |
| `frontend/app/client-navigation.tsx` | U | ver matriz |
| `frontend/app/client-shell.tsx` | U | ver matriz |
| `frontend/app/face-region-viewer.tsx` | U | ver matriz |
| `frontend/app/facial-search-client.ts` | U | ver matriz |
| `frontend/app/facial-search-storage.ts` | U | ver matriz |
| `frontend/app/gallery/[galleryId]/page.tsx` | U | ver matriz |
| `frontend/app/gallery/layout.tsx` | U | ver matriz |
| `frontend/app/gallery-card-preview.tsx` | U | ver matriz |
| `frontend/app/gallery-fonts.ts` | U | ver matriz |
| `frontend/app/gallery-presentation.tsx` | U | ver matriz |
| `frontend/app/install-app.tsx` | U | ver matriz |
| `frontend/app/layout.tsx` | U | ver matriz |
| `frontend/app/library/cart/mercadopago-resume.tsx` | U | ver matriz |
| `frontend/app/library/cart/page.tsx` | U | ver matriz |
| `frontend/app/library/checkout/card-payment.tsx` | U | ver matriz |
| `frontend/app/library/checkout/page.tsx` | U | ver matriz |
| `frontend/app/library/layout.tsx` | U | ver matriz |
| `frontend/app/library/loading.tsx` | U | ver matriz |
| `frontend/app/library/mercadopago.ts` | U | ver matriz |
| `frontend/app/library/page.tsx` | U | ver matriz |
| `frontend/app/library/payment-logo.tsx` | U | ver matriz |
| `frontend/app/library/purchase-card.tsx` | U | ver matriz |
| `frontend/app/library/purchases/page.tsx` | U | ver matriz |
| `frontend/app/manifest.ts` | U | ver matriz |
| `frontend/app/media-archive-status.ts` | U | ver matriz |
| `frontend/app/monitor-activity.tsx` | U | ver matriz |
| `frontend/app/order-album-url.ts` | U | ver matriz |
| `frontend/app/page.tsx` | U | ver matriz |
| `frontend/app/photographer-onboarding-gate.ts` | U | ver matriz |
| `frontend/app/photographer-signup/page.tsx` | U | ver matriz |
| `frontend/app/photographer-signup/turnstile-widget.tsx` | U | ver matriz |
| `frontend/app/product-brand.ts` | U | ver matriz |
| `frontend/app/protected-photo-viewer.tsx` | U | ver matriz |
| `frontend/app/public-galleries/[galleryId]/page.tsx` | U | ver matriz |
| `frontend/app/public-galleries/facial-search-panel.tsx` | U | ver matriz |
| `frontend/app/purchase-preview.tsx` | U | ver matriz |
| `frontend/app/push-control.tsx` | U | ver matriz |
| `frontend/app/push-device.ts` | U | ver matriz |
| `frontend/app/removed-movements.tsx` | U | ver matriz |
| `frontend/app/selection-deadline.tsx` | U | ver matriz |
| `frontend/app/session-boundary.tsx` | U | ver matriz |
| `frontend/app/session-recovery.ts` | U | ver matriz |
| `frontend/app/theme-control.tsx` | U | ver matriz |
| `frontend/app/theme.ts` | U | ver matriz |
| `frontend/app/ui-kit.tsx` | U | ver matriz |
| `frontend/app/upload-jpeg.ts` | U | ver matriz |
| `frontend/app/use-folder-access-clock.ts` | U | ver matriz |
| `frontend/app/validation-ui.tsx` | U | ver matriz |
| `frontend/public/markina-sw.js` | U | ver matriz |

## Rotas HTTP

| Rota | Escopo/critério | Fonte/handler | Dependências atuais | Evidência por critério |
| --- | --- | --- | --- | --- |
| `GET /admin/photo-folders/{folder_id}/processing` | R/P | `backend/app/folder_processing_api.py:47` / `configuration` | sem Depends na assinatura | ver matriz |
| `PATCH /admin/photo-folders/{folder_id}/processing` | R/P | `backend/app/folder_processing_api.py:102` / `save` | sem Depends na assinatura | ver matriz |
| `POST /admin/photo-folders/{folder_id}/processing/preview/enqueue` | R/P | `backend/app/folder_processing_api.py:119` / `enqueue_folder_preview` | sem Depends na assinatura | ver matriz |
| `POST /admin/photo-folders/{folder_id}/processing/facial/reprocess` | R/F | `backend/app/folder_processing_api.py:139` / `reprocess_folder_facial` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/drive/status` | I/O | `backend/app/google_drive_oauth.py:103` / `status` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/drive/observe-quota` | I/O | `backend/app/google_drive_oauth.py:156` / `observe_quota` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/drive/connect` | I/O | `backend/app/google_drive_oauth.py:188` / `connect` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/drive/oauth/callback` | I/O | `backend/app/google_drive_oauth.py:238` / `callback` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/drive/revoke` | I/O | `backend/app/google_drive_oauth.py:295` / `revoke` | sem Depends na assinatura | ver matriz |
| `GET /health` | I/I | `backend/app/main.py:1312` / `health` | sem Depends na assinatura | ver matriz |
| `POST /internal/whatsapp/webhook` | R/N | `backend/app/main.py:1317` / `whatsapp_webhook` | db_session | ver matriz |
| `GET /admin/whatsapp/channel` | R/N | `backend/app/main.py:1354` / `admin_whatsapp_channel` | db_session | ver matriz |
| `POST /admin/whatsapp/channel/provision` | R/N | `backend/app/main.py:1369` / `provision_admin_whatsapp_channel` | db_session | ver matriz |
| `PATCH /admin/whatsapp/channel` | R/N | `backend/app/main.py:1418` / `update_admin_whatsapp_channel` | db_session | ver matriz |
| `POST /admin/whatsapp/channel/refresh` | R/N | `backend/app/main.py:1432` / `refresh_admin_whatsapp_channel` | db_session | ver matriz |
| `POST /admin/whatsapp/channel/pairing` | R/N | `backend/app/main.py:1442` / `pair_admin_whatsapp_channel` | db_session | ver matriz |
| `GET /admin/whatsapp/deliveries` | R/N | `backend/app/main.py:1465` / `admin_whatsapp_deliveries` | db_session | ver matriz |
| `POST /admin/whatsapp/deliveries/{delivery_id}/retry` | R/N | `backend/app/main.py:1491` / `retry_admin_whatsapp_delivery` | db_session | ver matriz |
| `POST /auth/client/challenge` | M/A | `backend/app/main.py:1699` / `client_challenge` | db_session | ver matriz |
| `POST /auth/client/resend` | M/A | `backend/app/main.py:1795` / `client_resend` | db_session | ver matriz |
| `POST /auth/client/verify` | M/A | `backend/app/main.py:1820` / `client_verify` | db_session | ver matriz |
| `POST /auth/admin/password` | M/A | `backend/app/main.py:2099` / `admin_password` | db_session | ver matriz |
| `POST /auth/admin/totp` | M/A | `backend/app/main.py:2142` / `admin_totp` | db_session | ver matriz |
| `POST /admin/security/totp/recovery-codes` | M/A | `backend/app/main.py:2207` / `issue_admin_totp_recovery_codes` | db_session | ver matriz |
| `POST /auth/admin/recovery/challenge` | M/A | `backend/app/main.py:2269` / `admin_recovery_challenge` | db_session | ver matriz |
| `POST /auth/admin/recovery/resend` | M/A | `backend/app/main.py:2310` / `admin_recovery_resend` | db_session | ver matriz |
| `POST /auth/admin/recovery/verify` | M/A | `backend/app/main.py:2333` / `admin_recovery_verify` | db_session | ver matriz |
| `POST /auth/admin/recovery/reset` | M/A | `backend/app/main.py:2358` / `admin_recovery_reset` | db_session | ver matriz |
| `POST /auth/admin/email/confirm` | M/A | `backend/app/main.py:2440` / `confirm_admin_email` | db_session | ver matriz |
| `GET /auth/destination` | M/A | `backend/app/main.py:2488` / `destination` | sem Depends na assinatura | ver matriz |
| `GET /auth/identity` | M/A | `backend/app/main.py:2503` / `authenticated_identity` | db_session | ver matriz |
| `POST /auth/logout` | M/A | `backend/app/main.py:2534` / `logout` | sem Depends na assinatura | ver matriz |
| `POST /auth/revoke-all` | M/A | `backend/app/main.py:2554` / `revoke_all` | sem Depends na assinatura | ver matriz |
| `GET /admin` | M/A | `backend/app/main.py:2565` / `admin_area` | sem Depends na assinatura | ver matriz |
| `GET /admin/email/channel` | M/A | `backend/app/main.py:2571` / `admin_email_channel` | db_session | ver matriz |
| `GET /admin/security/summary` | M/A | `backend/app/main.py:2596` / `admin_security_summary` | db_session | ver matriz |
| `GET /admin/settings/pix` | R/K | `backend/app/main.py:2623` / `admin_global_pix` | db_session | ver matriz |
| `POST /admin/settings/pix/challenge` | R/K | `backend/app/main.py:2630` / `admin_global_pix_challenge` | db_session | ver matriz |
| `POST /admin/settings/pix/confirm` | R/K | `backend/app/main.py:2677` / `admin_global_pix_confirm` | db_session | ver matriz |
| `POST /admin/security/password/challenge` | M/A | `backend/app/main.py:2712` / `admin_password_change_challenge` | db_session | ver matriz |
| `POST /admin/security/password/confirm` | M/A | `backend/app/main.py:2745` / `admin_password_change_confirm` | db_session | ver matriz |
| `POST /admin/security/email/challenge` | M/A | `backend/app/main.py:2778` / `admin_email_change_challenge` | db_session | ver matriz |
| `POST /admin/security/email/verify-otp` | M/A | `backend/app/main.py:2817` / `admin_email_change_verify_otp` | db_session | ver matriz |
| `GET /branding` | M/K | `backend/app/main.py:2875` / `public_branding` | db_session | ver matriz |
| `GET /admin/branding` | M/K | `backend/app/main.py:2887` / `admin_branding` | db_session | ver matriz |
| `PATCH /admin/branding` | M/K | `backend/app/main.py:2897` / `update_admin_branding` | db_session | ver matriz |
| `PATCH /admin/branding/protection` | M/K | `backend/app/main.py:2911` / `update_visual_protection` | db_session | ver matriz |
| `PUT /admin/branding/{asset}` | M/K | `backend/app/main.py:2938` / `upload_branding_asset` | db_session | ver matriz |
| `GET /branding/{asset}` | M/K | `backend/app/main.py:2967` / `public_branding_asset` | db_session | ver matriz |
| `GET /admin/validation-summary` | R/L | `backend/app/main.py:3032` / `admin_validation_summary` | db_session | ver matriz |
| `GET /admin/credits/capabilities` | R/S | `backend/app/main.py:3427` / `admin_credit_capabilities` | db_session | ver matriz |
| `GET /admin/credits/wallet` | R/S | `backend/app/main.py:3438` / `admin_credit_wallet` | db_session | ver matriz |
| `GET /admin/media-archive/recovery-pricing` | R/L | `backend/app/main.py:3446` / `admin_media_archive_recovery_pricing` | db_session | ver matriz |
| `GET /admin/media-archive/recovery-candidates` | R/L | `backend/app/main.py:3456` / `admin_media_archive_recovery_candidates` | db_session | ver matriz |
| `GET /admin/media-archive/recoveries` | R/L | `backend/app/main.py:3469` / `admin_media_archive_recoveries` | db_session | ver matriz |
| `POST /admin/media-archive/cycles/{cycle_id}/recovery` | R/L | `backend/app/main.py:3481` / `admin_request_media_archive_recovery` | db_session | ver matriz |
| `GET /admin/credits/history` | R/S | `backend/app/main.py:3505` / `admin_credit_history` | db_session | ver matriz |
| `GET /admin/credits/history/folders/{folder_id}` | R/S | `backend/app/main.py:3516` / `admin_credit_folder_history` | db_session | ver matriz |
| `GET /admin/credits/packages` | R/S | `backend/app/main.py:3527` / `admin_active_credit_packages` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/credit-operation` | R/G | `backend/app/main.py:3544` / `admin_photo_credit_operation` | db_session | ver matriz |
| `GET /admin/credits/entries` | R/S | `backend/app/main.py:3573` / `admin_credit_entries` | db_session | ver matriz |
| `GET /admin/platform/credit-packages` | I/O | `backend/app/main.py:3583` / `admin_credit_packages` | db_session | ver matriz |
| `POST /admin/platform/credit-packages` | I/O | `backend/app/main.py:3591` / `admin_create_credit_package` | db_session | ver matriz |
| `PUT /admin/platform/credit-packages/{package_id}` | I/O | `backend/app/main.py:3615` / `admin_update_credit_package` | db_session | ver matriz |
| `GET /admin/platform/credit-tenants` | I/O | `backend/app/main.py:3640` / `admin_credit_tenants` | db_session | ver matriz |
| `GET /admin/platform/credit-tenants/search` | I/O | `backend/app/main.py:3648` / `admin_search_credit_tenants` | db_session | ver matriz |
| `GET /admin/platform/credit-tenants/{tenant_id}` | I/O | `backend/app/main.py:3664` / `admin_credit_tenant_detail` | db_session | ver matriz |
| `GET /admin/platform/credit-tenants/{tenant_id}/history` | I/O | `backend/app/main.py:3681` / `admin_owner_credit_history` | db_session | ver matriz |
| `GET /admin/platform/credit-tenants/{tenant_id}/history/folders/{folder_id}` | I/O | `backend/app/main.py:3691` / `admin_owner_credit_folder_history` | db_session | ver matriz |
| `GET /admin/platform/credit-purchases/reviews` | I/O | `backend/app/main.py:3701` / `admin_credit_purchase_reviews` | db_session | ver matriz |
| `POST /admin/platform/credit-purchases/{purchase_id}/review` | I/O | `backend/app/main.py:3716` / `admin_review_credit_purchase` | db_session | ver matriz |
| `POST /admin/platform/credit-grants` | I/O | `backend/app/main.py:3744` / `admin_grant_photographer_credits` | db_session | ver matriz |
| `POST /admin/platform/credit-grants/{grant_entry_id}/revoke` | I/O | `backend/app/main.py:3761` / `admin_revoke_photographer_credits` | db_session | ver matriz |
| `GET /admin/installation-capabilities` | I/O | `backend/app/main.py:3780` / `admin_installation_capabilities` | sem Depends na assinatura | ver matriz |
| `GET /admin/capacity-observability` | I/O | `backend/app/main.py:3791` / `admin_capacity_observability` | sem Depends na assinatura | ver matriz |
| `GET /admin/facial-observability` | I/O | `backend/app/main.py:3804` / `admin_facial_observability` | db_session | ver matriz |
| `GET /admin/clients` | R/C | `backend/app/main.py:3832` / `admin_clients` | db_session | ver matriz |
| `POST /admin/clients` | R/C | `backend/app/main.py:3847` / `create_client` | db_session | ver matriz |
| `PATCH /admin/clients/{client_id}` | R/C | `backend/app/main.py:3878` / `update_client_name` | db_session | ver matriz |
| `GET /admin/clients/{client_id}/deletion-inventory` | R/L | `backend/app/main.py:3895` / `get_client_deletion_inventory` | db_session | ver matriz |
| `DELETE /admin/clients/{client_id}` | R/L | `backend/app/main.py:3907` / `delete_client` | db_session | ver matriz |
| `GET /admin/parent-galleries` | R/G | `backend/app/main.py:4032` / `admin_parent_galleries` | db_session | ver matriz |
| `GET /admin/parent-galleries/overview` | R/G | `backend/app/main.py:4051` / `parent_gallery_overview` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/editor` | R/G | `backend/app/main.py:4377` / `parent_gallery_editor` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/settings` | R/G | `backend/app/main.py:4486` / `parent_gallery_settings` | db_session | ver matriz |
| `PATCH /admin/parent-galleries/{parent_gallery_id}/settings` | R/G | `backend/app/main.py:4512` / `update_parent_gallery_settings` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/summary` | R/G | `backend/app/main.py:4544` / `parent_gallery_summary` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/cover` | R/G | `backend/app/main.py:4602` / `set_parent_gallery_cover` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/cover` | R/G | `backend/app/main.py:4654` / `clear_parent_gallery_cover` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/sales` | R/S | `backend/app/main.py:4674` / `parent_gallery_sales` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/sales` | R/S | `backend/app/main.py:4698` / `update_parent_gallery_sales` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/details` | R/G | `backend/app/main.py:4726` / `parent_gallery_details` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/cover-photos` | R/G | `backend/app/main.py:4783` / `register_parent_gallery_cover_photo` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-policy` | R/F | `backend/app/main.py:4839` / `admin_parent_gallery_facial_policy` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/facial-policy` | R/F | `backend/app/main.py:4857` / `prepare_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/activate` | R/F | `backend/app/main.py:4889` / `activate_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/suspend` | R/F | `backend/app/main.py:4928` / `suspend_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/revoke` | R/F | `backend/app/main.py:4953` / `revoke_parent_gallery_facial_policy` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-cleanup-proof` | R/F | `backend/app/main.py:4978` / `admin_parent_gallery_facial_cleanup_proof` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-index` | R/F | `backend/app/main.py:4990` / `admin_parent_gallery_facial_index` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/facial-index` | R/F | `backend/app/main.py:5063` / `admin_private_gallery_facial_index` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-index/retry` | R/F | `backend/app/main.py:5134` / `retry_parent_gallery_facial_index` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-index/reprocess` | R/F | `backend/app/main.py:5174` / `reprocess_parent_gallery_facial_index` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:5229` / `admin_parent_gallery_photos` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/available-photos` | R/G | `backend/app/main.py:5252` / `admin_parent_gallery_available_photos` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/private-folders` | R/G | `backend/app/main.py:5326` / `admin_parent_gallery_private_folders` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/folders` | R/G | `backend/app/main.py:5338` / `admin_parent_gallery_folders` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/folders` | R/G | `backend/app/main.py:5448` / `create_photo_folder` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders` | R/G | `backend/app/main.py:5515` / `admin_client_restricted_folders` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders` | R/G | `backend/app/main.py:5574` / `create_admin_client_restricted_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}` | R/G | `backend/app/main.py:5641` / `grant_restricted_folder_client` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}` | R/L | `backend/app/main.py:5706` / `revoke_restricted_folder_client` | db_session | ver matriz |
| `PATCH /admin/photo-folders/{folder_id}` | R/G | `backend/app/main.py:5747` / `rename_photo_folder` | db_session | ver matriz |
| `PATCH /admin/photo-folders/{folder_id}/renew-deadline` | R/G | `backend/app/main.py:5772` / `renew_public_photo_folder_deadline` | db_session | ver matriz |
| `PATCH /admin/photo-folders/{folder_id}/deadline` | R/G | `backend/app/main.py:5827` / `configure_photo_folder_deadline` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}` | R/L | `backend/app/main.py:5870` / `delete_photo_folder` | db_session | ver matriz |
| `GET /admin/photo-folders/{folder_id}/photos` | R/G | `backend/app/main.py:5914` / `admin_photo_folder_photos` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}/photos/{photo_id}` | R/L | `backend/app/main.py:5979` / `delete_folder_photo_asset` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}/photos` | R/L | `backend/app/main.py:6104` / `delete_folder_photo_assets` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/photos` | R/G | `backend/app/main.py:6137` / `register_folder_photo_asset` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/publish` | R/G | `backend/app/main.py:6367` / `publish_photo_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/publish-ready` | R/G | `backend/app/main.py:6392` / `publish_parent_gallery_ready_photos` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/release` | R/G | `backend/app/main.py:6427` / `release_photo_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries` | R/G | `backend/app/main.py:6460` / `create_parent_gallery` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:6511` / `parent_gallery_public_link_status` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:6540` / `issue_parent_gallery_public_link` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/public-link/rotate` | R/G | `backend/app/main.py:6570` / `rotate_parent_gallery_public_link` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:6604` / `revoke_parent_gallery_public_link` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite` | R/G | `backend/app/main.py:6655` / `issue_parent_gallery_client_invite` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite/rotate` | R/G | `backend/app/main.py:6682` / `rotate_parent_gallery_client_invite` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite` | R/L | `backend/app/main.py:6717` / `revoke_parent_gallery_client_invite` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/deletion-inventory` | R/L | `backend/app/main.py:6809` / `parent_gallery_deletion_inventory` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/unlink-inventory` | R/L | `backend/app/main.py:6841` / `parent_gallery_client_unlink_inventory` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}` | R/G | `backend/app/main.py:6893` / `delete_parent_gallery` | db_session | ver matriz |
| `GET /admin/gallery-lifecycle-operations/{operation_id}` | R/L | `backend/app/main.py:6950` / `gallery_lifecycle_operation_status` | db_session | ver matriz |
| `POST /admin/gallery-lifecycle-operations/{operation_id}/retry` | R/L | `backend/app/main.py:6962` / `retry_gallery_lifecycle_operation` | db_session | ver matriz |
| `POST /admin/gallery-lifecycle-operations/{operation_id}/cancel` | R/L | `backend/app/main.py:6993` / `cancel_gallery_lifecycle_operation` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/clone` | R/G | `backend/app/main.py:7060` / `clone_derived_gallery` | db_session | ver matriz |
| `POST /admin/clients/{client_id}/phone/challenge` | R/C | `backend/app/main.py:7082` / `challenge_client_phone` | db_session | ver matriz |
| `POST /admin/clients/{client_id}/phone` | R/C | `backend/app/main.py:7103` / `change_client_phone` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients` | R/G | `backend/app/main.py:7135` / `parent_gallery_clients` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}` | R/G | `backend/app/main.py:7419` / `link_admin_client_to_parent_gallery` | db_session | ver matriz |
| `PATCH /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/access` | R/G | `backend/app/main.py:7448` / `update_admin_client_gallery_access` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}` | R/L | `backend/app/main.py:7489` / `unlink_admin_client_from_parent_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/selection` | R/S | `backend/app/main.py:7583` / `selection_detail` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/selection/export.{format}` | R/L | `backend/app/main.py:7900` / `export_selection` | db_session | ver matriz |
| `GET /admin/orders/{order_id}/selection/export.{format}` | R/L | `backend/app/main.py:7996` / `export_finalized_order` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/selection/export.{format}` | R/L | `backend/app/main.py:8018` / `export_canonical_selection` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:8131` / `register_photo_asset` | db_session | ver matriz |
| `PUT /admin/photo-assets/{photo_id}/source` | R/G | `backend/app/main.py:8184` / `import_photo_source` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/media-status` | R/G | `backend/app/main.py:8543` / `photo_media_status` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/facial-analysis` | R/F | `backend/app/main.py:8564` / `admin_photo_facial_analysis` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/preview` | R/G | `backend/app/main.py:8588` / `admin_photo_preview` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/watermarked-preview` | R/G | `backend/app/main.py:8618` / `admin_watermarked_photo_preview` | db_session | ver matriz |
| `GET /admin/purchases` | R/S | `backend/app/main.py:8650` / `admin_purchase_history` | db_session | ver matriz |
| `GET /admin/pricing-presets` | R/K | `backend/app/main.py:8815` / `list_progressive_pricing_presets` | db_session | ver matriz |
| `POST /admin/pricing-presets` | R/K | `backend/app/main.py:8831` / `create_progressive_pricing_preset` | db_session | ver matriz |
| `PUT /admin/pricing-presets/{preset_id}` | R/K | `backend/app/main.py:8868` / `update_progressive_pricing_preset` | db_session | ver matriz |
| `DELETE /admin/pricing-presets/{preset_id}` | R/K | `backend/app/main.py:8895` / `deactivate_progressive_pricing_preset` | db_session | ver matriz |
| `POST /admin/pricing-presets/{preset_id}/activate` | R/K | `backend/app/main.py:8911` / `activate_progressive_pricing_preset` | db_session | ver matriz |
| `GET /admin/pricing-presets/{preset_id}/quote` | R/K | `backend/app/main.py:8928` / `simulate_progressive_pricing_preset` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/pricing` | R/K | `backend/app/main.py:9142` / `admin_parent_gallery_pricing` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/pricing` | R/K | `backend/app/main.py:9152` / `save_admin_parent_gallery_pricing` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/pricing` | R/K | `backend/app/main.py:9171` / `admin_gallery_pricing` | db_session | ver matriz |
| `PUT /admin/derived-galleries/{gallery_id}/pricing` | R/K | `backend/app/main.py:9190` / `save_admin_gallery_pricing` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/orders` | R/S | `backend/app/main.py:9207` / `admin_gallery_orders` | db_session | ver matriz |
| `POST /admin/derived-galleries` | R/G | `backend/app/main.py:9275` / `create_derived_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:9319` / `private_gallery_link_status` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:9363` / `issue_private_gallery_link` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/link/rotate` | R/G | `backend/app/main.py:9380` / `rotate_private_gallery_link` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:9400` / `revoke_private_gallery_link` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/invite/rotate` | R/G | `backend/app/main.py:9418` / `rotate_private_gallery_invite` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/invite` | R/G | `backend/app/main.py:9434` / `revoke_private_gallery_invite` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/members` | R/G | `backend/app/main.py:9496` / `private_gallery_members` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members` | R/G | `backend/app/main.py:9562` / `add_private_gallery_member` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members/{client_id}/block` | R/G | `backend/app/main.py:9726` / `block_private_gallery_member` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members/{client_id}/unblock` | R/G | `backend/app/main.py:9745` / `unblock_private_gallery_member` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/members/{client_id}` | R/G | `backend/app/main.py:9764` / `unlink_private_gallery_member` | db_session | ver matriz |
| `GET /admin/notifications` | R/N | `backend/app/main.py:9783` / `admin_gallery_membership_notifications` | db_session | ver matriz |
| `POST /admin/notifications/{notification_id}/read` | R/N | `backend/app/main.py:9843` / `read_admin_gallery_membership_notification` | db_session | ver matriz |
| `GET /admin/media-archive/notices` | R/L | `backend/app/main.py:9857` / `list_admin_media_archive_notices` | db_session | ver matriz |
| `POST /admin/media-archive/notices/{notice_id}/read` | R/L | `backend/app/main.py:9916` / `read_admin_media_archive_notice` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/upload-batches` | R/G | `backend/app/main.py:9943` / `list_private_upload_batches` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/upload-batches` | R/G | `backend/app/main.py:9956` / `begin_private_upload_batch` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/upload-batches/{batch_id}/close` | R/G | `backend/app/main.py:9973` / `finish_private_upload_batch` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/upload-batches` | R/G | `backend/app/main.py:9989` / `begin_restricted_folder_upload_batch` | db_session | ver matriz |
| `GET /admin/photo-folders/{folder_id}/upload-batches` | R/G | `backend/app/main.py:10011` / `list_restricted_folder_upload_batches` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/upload-batches/{batch_id}/close` | R/G | `backend/app/main.py:10031` / `finish_restricted_folder_upload_batch` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/folders` | R/G | `backend/app/main.py:10046` / `admin_private_gallery_folders` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/folders` | R/G | `backend/app/main.py:10092` / `create_private_gallery_folder` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/photos` | R/G | `backend/app/main.py:10131` / `admin_private_gallery_photos` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/photos` | R/G | `backend/app/main.py:10340` / `add_admin_private_gallery_photos` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/photos/{photo_id}` | R/L | `backend/app/main.py:10360` / `remove_admin_private_gallery_photo` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:10427` / `delete_derived_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries` | R/G | `backend/app/main.py:10509` / `list_derived_galleries` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:10568` / `derived_gallery_detail` | db_session | ver matriz |
| `PATCH /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:10643` / `update_derived_gallery` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/renew` | R/G | `backend/app/main.py:10660` / `renew_gallery_selection` | db_session | ver matriz |
| `GET /admin/gallery-reopening-requests` | R/S | `backend/app/main.py:10723` / `list_gallery_reopening_requests` | db_session | ver matriz |
| `POST /admin/gallery-reopening-requests/{request_id}/decision` | R/S | `backend/app/main.py:10783` / `decide_gallery_reopening_request` | db_session | ver matriz |
| `POST /admin/gallery-reopening-notifications/{notification_id}/retry` | R/N | `backend/app/main.py:10863` / `retry_gallery_reopening_notification` | db_session | ver matriz |
| `GET /library` | R/G | `backend/app/main.py:10888` / `client_library` | db_session | ver matriz |
| `GET /library/cart` | R/S | `backend/app/main.py:11220` / `unified_cart` | db_session | ver matriz |
| `POST /library/cart/prepare` | R/S | `backend/app/main.py:11226` / `prepare_unified_cart` | db_session | ver matriz |
| `POST /library/cart/{gallery_id}/finalize` | R/S | `backend/app/main.py:11250` / `finalize_unified_selection` | db_session | ver matriz |
| `POST /library/payments/{group_id}/report` | R/S | `backend/app/main.py:11263` / `report_unified_payment` | db_session | ver matriz |
| `DELETE /library/cart/{gallery_id}` | R/S | `backend/app/main.py:11277` / `remove_unified_cart_group` | db_session | ver matriz |
| `DELETE /library/cart/{gallery_id}/photos/{photo_id}` | R/S | `backend/app/main.py:11307` / `remove_unified_cart_photo` | db_session | ver matriz |
| `GET /library/purchases` | R/S | `backend/app/main.py:11335` / `client_purchase_history` | db_session | ver matriz |
| `GET /library/purchases/items/{item_id}/preview` | R/S | `backend/app/main.py:11583` / `client_purchased_photo_preview` | db_session | ver matriz |
| `GET /library/history/items/{item_id}/preview` | R/S | `backend/app/main.py:11624` / `client_historical_preview` | db_session | ver matriz |
| `GET /library/history/items/{item_id}/delivery` | R/S | `backend/app/main.py:11641` / `client_historical_delivery` | db_session | ver matriz |
| `GET /gallery/{gallery_id}` | R/G | `backend/app/main.py:11671` / `gallery_area` | sem Depends na assinatura | ver matriz |
| `GET /gallery/{gallery_id}/photos` | R/G | `backend/app/main.py:11701` / `gallery_photos` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/folders` | R/G | `backend/app/main.py:11755` / `gallery_released_folders` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/review` | R/S | `backend/app/main.py:11803` / `gallery_review` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/cover-preview` | R/G | `backend/app/main.py:11930` / `client_gallery_cover_preview` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/photos/{photo_id}/preview` | R/G | `backend/app/main.py:12047` / `client_photo_preview` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:12117` / `select_photo` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:12195` / `select_photo_from_public_gallery` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:12251` / `unselect_photo_from_public_gallery` | db_session | ver matriz |
| `POST /public-gallery/access` | R/G | `backend/app/main.py:12341` / `access_public_gallery_with_session` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}` | R/G | `backend/app/main.py:12381` / `public_gallery_for_client` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-search` | R/F | `backend/app/main.py:12432` / `public_gallery_facial_search_availability` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos/{photo_id}/face-regions` | R/F | `backend/app/main.py:12471` / `public_photo_face_regions` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/face-region-searches` | R/F | `backend/app/main.py:12497` / `public_face_region_search` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/facial-searches` | R/F | `backend/app/main.py:12527` / `create_public_gallery_facial_search` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-searches/latest` | R/F | `backend/app/main.py:12607` / `latest_public_gallery_facial_search_result` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}` | R/F | `backend/app/main.py:12627` / `public_gallery_facial_search_result` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}` | R/F | `backend/app/main.py:12649` / `cancel_public_gallery_facial_search` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}/candidates/{photo_id}` | R/F | `backend/app/main.py:12679` / `reject_public_gallery_facial_candidate` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}/candidates/{photo_id}/selection` | R/F | `backend/app/main.py:12708` / `select_public_gallery_facial_candidate` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:12756` / `public_gallery_photos` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/cover-preview` | R/G | `backend/app/main.py:12894` / `public_gallery_cover_preview` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos/{photo_id}/preview` | R/G | `backend/app/main.py:12924` / `public_gallery_photo_preview` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:12999` / `favorite_canonical_photo` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:13031` / `unfavorite_canonical_photo` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/view` | R/S | `backend/app/main.py:13053` / `record_canonical_photo_view` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/comments` | R/S | `backend/app/main.py:13084` / `create_canonical_photo_comment` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/comments` | R/S | `backend/app/main.py:13110` / `canonical_client_comments` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:13141` / `remove_canonical_comment` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:13168` / `unselect_photo` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/cart` | R/S | `backend/app/main.py:13241` / `client_cart` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/reopening-requests` | R/S | `backend/app/main.py:13402` / `client_gallery_reopening_request` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/reopening-requests` | R/S | `backend/app/main.py:13432` / `request_gallery_reopening` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/reopening-requests` | R/S | `backend/app/main.py:13471` / `canonical_gallery_reopening_request` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/reopening-requests` | R/S | `backend/app/main.py:13501` / `request_canonical_gallery_reopening` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/checkout` | R/S | `backend/app/main.py:13540` / `checkout_gallery` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/orders/{order_id}/payment-communications` | R/S | `backend/app/main.py:13568` / `communicate_payment` | db_session | ver matriz |
| `POST /admin/payment-communications/{communication_id}/decision` | R/S | `backend/app/main.py:13666` / `decide_payment_communication` | db_session | ver matriz |
| `POST /admin/payment-communications/{communication_id}/correction` | R/S | `backend/app/main.py:13715` / `correct_payment_confirmation` | db_session | ver matriz |
| `PUT /admin/orders/{order_id}/delivery` | R/S | `backend/app/main.py:13833` / `update_order_delivery` | db_session | ver matriz |
| `POST /admin/orders/{order_id}/delivery/resend` | R/S | `backend/app/main.py:13849` / `resend_order_delivery` | db_session | ver matriz |
| `GET /push/subscription` | R/N | `backend/app/main.py:13871` / `push_subscription_state` | db_session | ver matriz |
| `POST /push/subscription` | R/N | `backend/app/main.py:13892` / `register_push_subscription` | db_session | ver matriz |
| `DELETE /push/subscription` | R/N | `backend/app/main.py:13919` / `unregister_push_subscription` | db_session | ver matriz |
| `GET /admin/notification-settings` | R/K | `backend/app/main.py:13947` / `list_notification_settings` | db_session | ver matriz |
| `PUT /admin/notification-settings/{event_type}` | R/K | `backend/app/main.py:13958` / `update_notification_setting` | db_session | ver matriz |
| `PUT /admin/payment-message-templates/{kind}` | R/K | `backend/app/main.py:13972` / `save_payment_template` | db_session | ver matriz |
| `GET /admin/payment-message-templates` | R/K | `backend/app/main.py:13989` / `list_payment_templates` | db_session | ver matriz |
| `GET /admin/payment-message-templates/migration-preview` | R/K | `backend/app/main.py:14004` / `preview_payment_template_migration_api` | db_session | ver matriz |
| `GET /admin/removed-photo-movements` | R/L | `backend/app/main.py:14014` / `admin_removed_photo_movements` | db_session | ver matriz |
| `GET /admin/orders/{order_id}/items/{item_id}/preview` | R/S | `backend/app/main.py:14041` / `admin_order_item_preview` | db_session | ver matriz |
| `GET /admin/payment-communications/export.csv` | R/L | `backend/app/main.py:14087` / `export_payment_orders` | db_session | ver matriz |
| `GET /admin/payment-communications` | R/S | `backend/app/main.py:14119` / `list_payment_communications` | db_session | ver matriz |
| `POST /admin/payment-notifications/{notification_id}/retry` | R/N | `backend/app/main.py:14826` / `retry_payment_notification` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/payment-communications` | R/S | `backend/app/main.py:14848` / `client_payment_communications` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/orders/{order_id}` | R/S | `backend/app/main.py:14868` / `client_pending_order` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:15011` / `favorite_photo` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:15047` / `unfavorite_photo` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/comments` | R/S | `backend/app/main.py:15068` / `create_photo_comment` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/comments` | R/S | `backend/app/main.py:15101` / `client_comments` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:15125` / `remove_own_comment` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/comments` | R/S | `backend/app/main.py:15148` / `admin_comments` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:15176` / `remove_comment_as_admin` | db_session | ver matriz |
| `GET /admin/settings/payment-providers` | R/S | `backend/app/mercadopago_api.py:190` / `get_settings` | db_session | ver matriz |
| `POST /admin/settings/payment-providers/challenge` | R/S | `backend/app/mercadopago_api.py:195` / `settings_challenge` | db_session | ver matriz |
| `POST /admin/settings/payment-providers/confirm` | R/S | `backend/app/mercadopago_api.py:232` / `settings_confirm` | db_session | ver matriz |
| `POST /admin/settings/payment-providers/resend` | R/S | `backend/app/mercadopago_api.py:261` / `settings_resend` | db_session | ver matriz |
| `GET /library/mercadopago/active` | R/S | `backend/app/mercadopago_api.py:292` / `active_checkout` | db_session | ver matriz |
| `POST /library/mercadopago/prepare` | R/S | `backend/app/mercadopago_api.py:298` / `prepare_checkout` | db_session | ver matriz |
| `GET /library/mercadopago/{payment_id}` | R/S | `backend/app/mercadopago_api.py:309` / `get_checkout` | db_session | ver matriz |
| `POST /library/mercadopago/{payment_id}/submit` | R/S | `backend/app/mercadopago_api.py:318` / `submit_checkout` | db_session | ver matriz |
| `POST /library/mercadopago/{payment_id}/reconcile` | R/S | `backend/app/mercadopago_api.py:324` / `reconcile_checkout` | db_session | ver matriz |
| `POST /library/mercadopago/{payment_id}/cancel` | R/S | `backend/app/mercadopago_api.py:329` / `cancel_checkout` | db_session | ver matriz |
| `GET /admin/credits/purchases` | R/S | `backend/app/mercadopago_api.py:334` / `credit_purchase_history` | db_session | ver matriz |
| `GET /admin/credits/purchases/active` | R/S | `backend/app/mercadopago_api.py:349` / `active_credit_purchases` | db_session | ver matriz |
| `POST /admin/credits/purchases/prepare` | R/S | `backend/app/mercadopago_api.py:363` / `prepare_credit_purchase_route` | db_session | ver matriz |
| `GET /admin/credits/purchases/{purchase_id}` | R/S | `backend/app/mercadopago_api.py:383` / `get_credit_purchase` | db_session | ver matriz |
| `POST /admin/credits/purchases/{purchase_id}/submit` | R/S | `backend/app/mercadopago_api.py:397` / `submit_credit_purchase_route` | db_session | ver matriz |
| `POST /admin/credits/purchases/{purchase_id}/reconcile` | R/S | `backend/app/mercadopago_api.py:418` / `reconcile_credit_purchase_route` | db_session | ver matriz |
| `POST /mercadopago/webhooks/{account_id}` | R/S | `backend/app/mercadopago_api.py:432` / `webhook` | db_session | ver matriz |
| `GET /admin/platform/console/tenants/{tenant_id}/access-recovery` | I/O | `backend/app/photographer_access_recovery.py:360` / `lookup` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/access-recovery` | I/O | `backend/app/photographer_access_recovery.py:374` / `start` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/access-recovery/{request_id}/commit` | I/O | `backend/app/photographer_access_recovery.py:396` / `commit` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-access-recovery/confirm` | M/A | `backend/app/photographer_access_recovery.py:419` / `confirm` | database | ver matriz |
| `GET /admin/onboarding` | R/A | `backend/app/photographer_onboarding.py:245` / `status` | sem Depends na assinatura | ver matriz |
| `GET /admin/onboarding/address` | R/A | `backend/app/photographer_onboarding.py:263` / `photographer_address` | sem Depends na assinatura | ver matriz |
| `PUT /admin/onboarding/address` | R/A | `backend/app/photographer_onboarding.py:270` / `reserve_photographer_address` | sem Depends na assinatura | ver matriz |
| `GET /admin/onboarding/terms` | R/A | `backend/app/photographer_onboarding.py:286` / `terms` | sem Depends na assinatura | ver matriz |
| `GET /admin/onboarding/checkout-identity` | R/A | `backend/app/photographer_onboarding.py:303` / `checkout_identity` | sem Depends na assinatura | ver matriz |
| `PUT /admin/onboarding/profile` | R/A | `backend/app/photographer_onboarding.py:323` / `save_profile` | sem Depends na assinatura | ver matriz |
| `POST /admin/onboarding/terms/test-acceptance` | R/A | `backend/app/photographer_onboarding.py:378` / `accept_local_test_terms` | sem Depends na assinatura | ver matriz |
| `POST /admin/onboarding/terms/accept` | R/A | `backend/app/photographer_onboarding.py:412` / `accept_published_terms` | sem Depends na assinatura | ver matriz |
| `GET /admin/onboarding/terms/acceptances` | R/A | `backend/app/photographer_onboarding.py:455` / `own_term_acceptances` | sem Depends na assinatura | ver matriz |
| `GET /admin/onboarding/terms/acceptances/{acceptance_id}/copy` | R/A | `backend/app/photographer_onboarding.py:467` / `download_own_term_acceptance` | sem Depends na assinatura | ver matriz |
| `GET /auth/photographer-signup/config` | M/A | `backend/app/photographer_signup.py:164` / `signup_public_config` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-signup/recovery/email-link` | M/A | `backend/app/photographer_signup.py:208` / `request_email_recovery` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-signup` | M/A | `backend/app/photographer_signup.py:234` / `start` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-signup/verify-email` | M/A | `backend/app/photographer_signup.py:283` / `verify_email` | sem Depends na assinatura | ver matriz |
| `GET /auth/photographer-signup/setup` | M/A | `backend/app/photographer_signup.py:324` / `setup` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-signup/complete` | M/A | `backend/app/photographer_signup.py:331` / `complete` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-signup/cancel` | M/A | `backend/app/photographer_signup.py:368` / `cancel` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/terms/draft` | I/A | `backend/app/photographer_terms.py:89` / `get_draft` | sem Depends na assinatura | ver matriz |
| `PUT /admin/platform/terms/draft` | I/A | `backend/app/photographer_terms.py:101` / `save_draft` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/terms/versions` | I/A | `backend/app/photographer_terms.py:141` / `list_versions` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/terms/acceptances/{tenant_id}` | I/A | `backend/app/photographer_terms.py:155` / `list_tenant_acceptances` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/terms/publish` | I/A | `backend/app/photographer_terms.py:170` / `publish` | sem Depends na assinatura | ver matriz |
| `POST /admin/security/totp/enrollment` | M/A | `backend/app/photographer_totp.py:117` / `begin` | sem Depends na assinatura | ver matriz |
| `POST /admin/security/totp/enrollment/confirm` | M/A | `backend/app/photographer_totp.py:151` / `confirm` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/tenants/{tenant_id}/totp-support` | I/O | `backend/app/photographer_totp_support.py:69` / `target` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/photographers/{admin_id}/revoke-totp` | I/O | `backend/app/photographer_totp_support.py:167` / `revoke` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/capabilities` | I/O | `backend/app/platform_console.py:187` / `capabilities` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/tenants` | I/O | `backend/app/platform_console.py:199` / `tenants` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/tenants/{tenant_id}` | I/O | `backend/app/platform_console.py:209` / `detail` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/tenants/{tenant_id}/closure` | I/O | `backend/app/platform_console.py:216` / `tenant_closure_status` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/closure/profile-reduction` | I/O | `backend/app/platform_console.py:225` / `reduce_tenant_profile` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/closure/media-deletion` | I/O | `backend/app/platform_console.py:284` / `request_tenant_media_deletion` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/closure/media-deletion/retry` | I/O | `backend/app/platform_console.py:368` / `retry_tenant_media_deletion` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/closure/recovery-batches` | I/O | `backend/app/platform_console.py:459` / `request_tenant_closure_recovery` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/tenants/{tenant_id}/closure/recovery-batches/{batch_id}` | I/O | `backend/app/platform_console.py:534` / `tenant_closure_recovery_status` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/closure/reopen` | I/O | `backend/app/platform_console.py:551` / `reopen_tenant_account` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/sources` | I/O | `backend/app/platform_console.py:616` / `sources` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/status` | I/O | `backend/app/platform_console.py:829` / `status` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/tenants/{tenant_id}/hostname/activate` | I/O | `backend/app/platform_console.py:842` / `activate_hostname` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/media-archive/recovery-pricing` | I/O | `backend/app/platform_console.py:855` / `media_archive_recovery_pricing` | sem Depends na assinatura | ver matriz |
| `PUT /admin/platform/console/media-archive/recovery-pricing` | I/O | `backend/app/platform_console.py:864` / `update_media_archive_recovery_pricing` | sem Depends na assinatura | ver matriz |
| `POST /admin/platform/console/credit-tenants/{tenant_id}/media-archive/recoveries/{operation_id}/retry` | I/O | `backend/app/platform_console.py:914` / `retry_media_archive_recovery` | sem Depends na assinatura | ver matriz |
| `GET /admin/platform/console/audit` | I/O | `backend/app/platform_console.py:978` / `audit_events` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/galleries/{gallery_id}/configuration` | R/P | `backend/app/preview_adjustment/api.py:34` / `configuration` | sem Depends na assinatura | ver matriz |
| `PATCH /admin/preview-adjustment/galleries/{gallery_id}/configuration` | R/P | `backend/app/preview_adjustment/api.py:49` / `save_configuration` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/galleries` | R/P | `backend/app/preview_adjustment/api.py:65` / `galleries` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/galleries/{gallery_id}` | R/P | `backend/app/preview_adjustment/api.py:84` / `gallery_progress` | sem Depends na assinatura | ver matriz |
| `POST /admin/preview-adjustment/galleries/{gallery_id}/enqueue` | R/P | `backend/app/preview_adjustment/api.py:122` / `enqueue_gallery` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/photos/{photo_id}/{version}` | R/P | `backend/app/preview_adjustment/api.py:160` / `compare` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/capabilities` | I/O | `backend/app/system_monitor/routes.py:48` / `capabilities` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor` | I/O | `backend/app/system_monitor/routes.py:56` / `summary` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/tree` | I/O | `backend/app/system_monitor/routes.py:63` / `tree` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/incidents` | I/O | `backend/app/system_monitor/routes.py:79` / `incidents` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/report` | I/O | `backend/app/system_monitor/routes.py:87` / `report` | sem Depends na assinatura | ver matriz |
| `GET /auth/activity-policy` | M/A | `backend/app/system_monitor/routes.py:108` / `activity_policy` | sem Depends na assinatura | ver matriz |
| `POST /auth/activity` | M/A | `backend/app/system_monitor/routes.py:117` / `activity` | sem Depends na assinatura | ver matriz |
| `GET /admin/closure` | R/L | `backend/app/tenant_closure_api.py:102` / `closure_status` | sem Depends na assinatura | ver matriz |
| `POST /admin/closure` | R/L | `backend/app/tenant_closure_api.py:140` / `submit_closure` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-closure-identity/request` | M/A | `backend/app/tenant_closure_identity.py:205` / `request_identity_verification` | sem Depends na assinatura | ver matriz |
| `POST /auth/photographer-closure-identity/confirm` | M/A | `backend/app/tenant_closure_identity.py:314` / `confirm_identity_verification` | sem Depends na assinatura | ver matriz |
| `GET /local-demo/mailbox` | T/T | `scripts/local_photographer_demo.py:228` / `local_mailbox` | sem Depends na assinatura | ver matriz |
| `POST /local-demo/simulate-credit-purchase` | T/T | `scripts/local_photographer_demo.py:252` / `simulate_credit_purchase` | sem Depends na assinatura | ver matriz |
| `POST /local-demo/configure-upload-prerequisites` | T/T | `scripts/local_photographer_demo.py:269` / `configure_upload_prerequisites` | sem Depends na assinatura | ver matriz |

## Produtores queries gates e efeitos

| Fonte/função | Critério/teste | Sinal | Chamada | Evidência por critério |
| --- | --- | --- | --- | --- |
| `backend/app/acervo_context.py:14` / `require_active_owner` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/acervo_context.py:33` / `owned_record` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/acervo_context.py:34` / `owned_record` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/acervo_context.py:41` / `client_tenant_id` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/acervo_context.py:44` / `client_tenant_id` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/acervo_context.py:18` / `require_active_owner` | G | query/ORM | `db.info.get` | ver matriz |
| `backend/app/acervo_context.py:22` / `require_active_owner` | G | query/ORM | `db.info.get` | ver matriz |
| `backend/app/acervo_context.py:34` / `owned_record` | G | query/ORM | `select` | ver matriz |
| `backend/app/admin_account.py:94` / `_queue_admin_otp` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/admin_account.py:96` / `_queue_admin_otp` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/admin_account.py:97` / `_queue_admin_otp` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/admin_account.py:101` / `_queue_admin_otp` | A | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/admin_account.py:122` / `_queue_admin_otp` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/admin_account.py:163` / `create_security_challenge` | A | produtor | `AdminSecurityChallenge` | ver matriz |
| `backend/app/admin_account.py:178` / `create_security_challenge` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/admin_account.py:196` / `verify_security_challenge` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:228` / `resend_security_challenge` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:279` / `issue_password_reset_link` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:300` / `issue_password_reset_email` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:309` / `challenge_target` | A | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:313` / `challenge_target` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/admin_account.py:322` / `token_target` | A | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:326` / `token_target` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/admin_account.py:348` / `issue_email_verification` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/admin_account.py:357` / `issue_email_verification` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:375` / `queue_previous_email_notice` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:400` / `active_admin_for_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:113` / `_queue_admin_otp` | A | efeito potencial | `encrypt_otp` | ver matriz |
| `backend/app/admin_account.py:137` / `create_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:138` / `create_security_challenge` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/admin_account.py:152` / `create_security_challenge` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_account.py:175` / `create_security_challenge` | A | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:200` / `verify_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:232` / `resend_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:395` / `active_admin_for_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/admin_account.py:97` / `_queue_admin_otp` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_account.py:114` / `_queue_admin_otp` | A | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/admin_account.py:348` / `issue_email_verification` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_account.py:52` / `require_security_owner` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/admin_account.py:141` / `create_security_challenge` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/admin_account.py:153` / `create_security_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:60` / `encrypt_sensitive_payload` | A | efeito potencial | `AESGCM(sensitive_payload_key()).encrypt` | ver matriz |
| `backend/app/admin_security.py:87` / `issue_admin_action_token` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:97` / `issue_admin_action_token` | A | produtor | `AdminActionToken` | ver matriz |
| `backend/app/admin_security.py:109` / `issue_admin_action_token` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/admin_security.py:120` / `consume_admin_action_token` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/admin_security.py:129` / `consume_admin_action_token` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/admin_security.py:144` / `invalidate_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:147` / `invalidate_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:155` / `invalidate_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:181` / `cleanup_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:67` / `decrypt_sensitive_payload` | A | efeito potencial | `AESGCM(sensitive_payload_key()).decrypt` | ver matriz |
| `backend/app/admin_security.py:106` / `issue_admin_action_token` | A | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_security.py:169` / `cleanup_admin_security_material` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/admin_security.py:174` / `cleanup_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:186` / `cleanup_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:190` / `cleanup_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:178` / `cleanup_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:186` / `cleanup_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:190` / `cleanup_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:203` / `cleanup_admin_security_material` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/admin_security.py:88` / `issue_admin_action_token` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:121` / `consume_admin_action_token` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:144` / `invalidate_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:148` / `invalidate_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:156` / `invalidate_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:174` / `cleanup_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:130` / `consume_admin_action_token` | A | query/ORM | `update` | ver matriz |
| `backend/app/app_env_transition.py:187` / `_backup_key` | K | query/ORM | `cipher._keys.get` | ver matriz |
| `backend/app/app_env_transition.py:190` / `_backup_key` | K | efeito potencial | `HKDF(algorithm=hashes.SHA256(), length=32, salt=b'markina-gallery-app-env-transition-v1', info=f'encrypted-backup:{key_id}'.encode()).derive` | ver matriz |
| `backend/app/app_env_transition.py:306` / `_open_transition_backup` | K | efeito potencial | `AESGCM(_backup_key(source, backup.key_id)).decrypt` | ver matriz |
| `backend/app/app_env_transition.py:367` / `_load_accounts` | K | query/ORM | `session.bind.get_execution_options().get` | ver matriz |
| `backend/app/app_env_transition.py:374` / `_load_accounts` | K | query/ORM | `session.execute` | ver matriz |
| `backend/app/app_env_transition.py:262` / `create_encrypted_transition_backup` | K | efeito potencial | `AESGCM(_backup_key(source, key_id)).encrypt` | ver matriz |
| `backend/app/app_env_transition.py:340` / `_open_transition_backup` | K | query/ORM | `seen_ids.add` | ver matriz |
| `backend/app/app_env_transition.py:343` / `_open_transition_backup` | K | efeito potencial | `source.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:344` / `_open_transition_backup` | K | efeito potencial | `source.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:368` / `_load_accounts` | K | query/ORM | `schema_map.get` | ver matriz |
| `backend/app/app_env_transition.py:374` / `_load_accounts` | K | query/ORM | `text` | ver matriz |
| `backend/app/app_env_transition.py:375` / `_load_accounts` | K | query/ORM | `select` | ver matriz |
| `backend/app/app_env_transition.py:386` / `_verify_envelopes` | K | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:387` / `_verify_envelopes` | K | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:378` / `_load_accounts` | K | query/ORM | `session.scalars` | ver matriz |
| `backend/app/app_env_transition.py:450` / `_execute_mercadopago_transition` | K | efeito potencial | `source.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:452` / `_execute_mercadopago_transition` | K | efeito potencial | `source.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:454` / `_execute_mercadopago_transition` | K | efeito potencial | `target.encrypt` | ver matriz |
| `backend/app/app_env_transition.py:456` / `_execute_mercadopago_transition` | K | efeito potencial | `target.encrypt` | ver matriz |
| `backend/app/app_env_transition.py:463` / `_execute_mercadopago_transition` | K | query/ORM | `session.execute` | ver matriz |
| `backend/app/app_env_transition.py:574` / `restore_mercadopago_transition_backup` | K | query/ORM | `session.execute` | ver matriz |
| `backend/app/app_env_transition.py:194` / `_backup_key` | K | efeito potencial | `f'encrypted-backup:{key_id}'.encode` | ver matriz |
| `backend/app/app_env_transition.py:458` / `_execute_mercadopago_transition` | K | efeito potencial | `target.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:460` / `_execute_mercadopago_transition` | K | efeito potencial | `target.decrypt` | ver matriz |
| `backend/app/app_env_transition.py:464` / `_execute_mercadopago_transition` | K | query/ORM | `update` | ver matriz |
| `backend/app/app_env_transition.py:575` / `restore_mercadopago_transition_backup` | K | query/ORM | `update` | ver matriz |
| `backend/app/asset_removal.py:54` / `preserve_asset_history` | L | gate | `owned_record` | ver matriz |
| `backend/app/asset_removal.py:101` / `historical_paths` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/asset_removal.py:114` / `historical_paths` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/asset_removal.py:127` / `enqueue_file_cleanup` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/asset_removal.py:141` / `enqueue_file_cleanup` | L | produtor | `AssetFileCleanup` | ver matriz |
| `backend/app/asset_removal.py:142` / `enqueue_file_cleanup` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/asset_removal.py:149` / `validate_cleanup_paths` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/asset_removal.py:178` / `process_file_cleanup` | L | gate | `owned_record` | ver matriz |
| `backend/app/asset_removal.py:211` / `delete_private_records` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/asset_removal.py:215` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:217` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:218` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:220` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:224` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:226` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:227` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:228` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:229` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:235` / `removed_movements_payload` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/asset_removal.py:264` / `removed_movements_page` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:40` / `lock_removal_clients` | L | gate | `owned_record` | ver matriz |
| `backend/app/asset_removal.py:47` / `lock_removal_clients` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/asset_removal.py:62` / `preserve_asset_history` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/asset_removal.py:85` / `preserve_asset_history` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/asset_removal.py:213` / `delete_private_records` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:55` / `preserve_asset_history` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/asset_removal.py:63` / `preserve_asset_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/asset_removal.py:66` / `preserve_asset_history` | L | gate | `owned_record` | ver matriz |
| `backend/app/asset_removal.py:67` / `preserve_asset_history` | L | query/ORM | `galleries.get` | ver matriz |
| `backend/app/asset_removal.py:70` / `preserve_asset_history` | L | gate | `owned_record` | ver matriz |
| `backend/app/asset_removal.py:71` / `preserve_asset_history` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/asset_removal.py:91` / `preserve_asset_history` | L | gate | `owned_record` | ver matriz |
| `backend/app/asset_removal.py:105` / `historical_paths` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:172` / `validate_cleanup_paths` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/asset_removal.py:198` / `process_file_cleanup` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/asset_removal.py:199` / `process_file_cleanup` | L | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/asset_removal.py:258` / `removed_movements_payload` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/asset_removal.py:71` / `preserve_asset_history` | L | produtor | `RemovedPhotoMovement` | ver matriz |
| `backend/app/asset_removal.py:94` / `preserve_asset_history` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/asset_removal.py:137` / `enqueue_file_cleanup` | L | query/ORM | `entries.add` | ver matriz |
| `backend/app/asset_removal.py:42` / `lock_removal_clients` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:44` / `lock_removal_clients` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:46` / `lock_removal_clients` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:79` / `preserve_asset_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:214` / `delete_private_records` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:236` / `removed_movements_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:59` / `preserve_asset_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:114` / `historical_paths` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:172` / `validate_cleanup_paths` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:215` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:217` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:218` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:226` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:227` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:228` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:229` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:213` / `delete_private_records` | L | query/ORM | `delete` | ver matriz |
| `backend/app/asset_removal.py:55` / `preserve_asset_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:63` / `preserve_asset_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:83` / `preserve_asset_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:109` / `historical_paths` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:112` / `historical_paths` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:220` / `delete_private_records` | L | query/ORM | `update` | ver matriz |
| `backend/app/asset_removal.py:224` / `delete_private_records` | L | query/ORM | `update` | ver matriz |
| `backend/app/asset_removal.py:264` / `removed_movements_page` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:47` / `lock_removal_clients` | L | query/ORM | `select` | ver matriz |
| `backend/app/asset_removal.py:94` / `preserve_asset_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5030` / `audit` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:5072` / `create_challenge` | A | produtor | `AuthChallenge` | ver matriz |
| `backend/app/auth.py:5084` / `create_challenge` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:5100` / `enqueue_client_otp_delivery` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:5102` / `enqueue_client_otp_delivery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:5108` / `enqueue_client_otp_delivery` | A | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/auth.py:5135` / `enqueue_client_otp_delivery` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:5172` / `resend_client_challenge` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:5173` / `resend_client_challenge` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:5193` / `resend_client_challenge` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:5222` / `consume_challenge` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:5266` / `minimize_client_challenge_pii` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:5286` / `cleanup_expired_client_otp_pii` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/auth.py:5333` / `create_session` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:5344` / `create_session` | A | produtor | `AuthSession` | ver matriz |
| `backend/app/auth.py:5353` / `create_session` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:5374` / `current_session` | A | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/auth.py:5423` / `revoke_subject_sessions` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:5430` / `revoke_subject_sessions` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:74` / `expired` | A | efeito potencial | `value.replace` | ver matriz |
| `backend/app/auth.py:94` / `_enable_sqlite_foreign_keys` | A | query/ORM | `cursor.execute` | ver matriz |
| `backend/app/auth.py:250` / `_decode_persisted_totp` | A | efeito potencial | `TotpSecretCipher.from_environment().decrypt` | ver matriz |
| `backend/app/auth.py:5030` / `audit` | A | produtor | `AuditEvent` | ver matriz |
| `backend/app/auth.py:5038` / `enforce_rate_limit` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:5070` / `create_challenge` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:5120` / `enqueue_client_otp_delivery` | A | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/auth.py:5121` / `enqueue_client_otp_delivery` | A | efeito potencial | `encrypt_otp` | ver matriz |
| `backend/app/auth.py:5144` / `require_client_channel` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/auth.py:5150` / `require_client_auth_tenant` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:5211` / `resend_client_challenge` | A | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/auth.py:5291` / `cleanup_expired_client_otp_pii` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:5301` / `cleanup_expired_client_otp_pii` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/auth.py:5378` / `current_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:239` / `_decode_persisted_totp` | A | efeito potencial | `TotpSecretCipher.from_environment().decrypt` | ver matriz |
| `backend/app/auth.py:2262` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2270` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2271` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2621` / `_materialize_required_commercial_snapshots` | A | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/auth.py:2629` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:2662` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:2673` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:4427` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4429` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4432` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4461` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4465` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4468` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4503` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4505` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4508` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4511` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4604` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4677` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4681` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4682` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4692` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4696` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4703` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4706` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4741` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4790` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4848` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4877` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:5218` / `consume_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5317` / `create_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/auth.py:5318` / `create_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:364` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:364` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:691` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:692` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:882` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:882` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:889` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:890` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:896` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:897` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1195` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1196` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1203` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1204` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1210` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1211` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1453` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1454` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1486` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1487` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1519` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1520` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1576` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1577` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1789` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1789` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1865` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1869` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1878` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1883` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2146` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2147` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2520` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2521` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2529` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2530` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2536` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2537` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2635` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:2646` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:2663` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:2678` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:2685` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:2926` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2927` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2933` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2934` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2939` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:2940` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4421` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4422` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4574` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4575` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4580` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:4581` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:5102` / `enqueue_client_otp_delivery` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5194` / `resend_client_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5267` / `minimize_client_challenge_pii` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5334` / `create_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5389` / `current_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/auth.py:5390` / `current_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:5423` / `revoke_subject_sessions` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5431` / `revoke_subject_sessions` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5039` / `enforce_rate_limit` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5292` / `cleanup_expired_client_otp_pii` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5326` / `create_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:5378` / `current_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5397` / `current_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:5173` / `resend_client_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5410` / `current_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:5326` / `create_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:5406` / `current_session` | A | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/auth.py:5410` / `current_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/branding_context.py:41` / `branding_settings` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/branding_context.py:45` / `branding_settings` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/branding_context.py:34` / `branding_tenant_id` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/branding_context.py:43` / `branding_settings` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/branding_context.py:44` / `branding_settings` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/branding_context.py:49` / `branding_settings` | K | produtor | `BrandingSettings` | ver matriz |
| `backend/app/branding_context.py:50` / `branding_settings` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/branding_context.py:20` / `branding_tenant_id` | K | gate | `owned_record` | ver matriz |
| `backend/app/branding_context.py:25` / `branding_tenant_id` | K | gate | `owned_record` | ver matriz |
| `backend/app/branding_context.py:45` / `branding_settings` | K | query/ORM | `select` | ver matriz |
| `backend/app/branding_context.py:43` / `branding_settings` | K | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:47` / `_selection_quantity` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/canonical_selection.py:63` / `select_canonical_photo` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/canonical_selection.py:64` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:75` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:134` / `unselect_canonical_photo` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/canonical_selection.py:146` / `unselect_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:147` / `unselect_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:153` / `unselect_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:51` / `_selection_quantity` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:96` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:108` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:159` / `unselect_canonical_photo` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/canonical_selection.py:80` / `select_canonical_photo` | S | produtor | `GalleryClientState` | ver matriz |
| `backend/app/canonical_selection.py:85` / `select_canonical_photo` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/canonical_selection.py:89` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:113` / `select_canonical_photo` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/canonical_selection.py:71` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:102` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:113` / `select_canonical_photo` | S | produtor | `PhotoSelection` | ver matriz |
| `backend/app/canonical_selection.py:121` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:153` / `unselect_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:52` / `_selection_quantity` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:64` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:146` / `unselect_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:147` / `unselect_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:97` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/collector.py:108` / `_read_session` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/collector.py:109` / `_read_session` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/collector.py:110` / `_read_session` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/collector.py:108` / `_read_session` | O | query/ORM | `text` | ver matriz |
| `backend/app/capacity_observability/collector.py:109` / `_read_session` | O | query/ORM | `text` | ver matriz |
| `backend/app/capacity_observability/collector.py:110` / `_read_session` | O | query/ORM | `text` | ver matriz |
| `backend/app/capacity_observability/collector.py:180` / `_collect_once` | O | query/ORM | `queue_snapshots.update` | ver matriz |
| `backend/app/capacity_observability/collector.py:189` / `_collect_once` | O | query/ORM | `queue_snapshots.update` | ver matriz |
| `backend/app/capacity_observability/collector.py:140` / `read_query` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/collector.py:168` / `_collect_once` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/collector.py:140` / `read_query` | O | query/ORM | `text` | ver matriz |
| `backend/app/capacity_observability/collector.py:168` / `_collect_once` | O | query/ORM | `text` | ver matriz |
| `backend/app/capacity_observability/collector.py:141` / `read_query` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/database.py:22` / `<módulo>` | O | query/ORM | `text` | ver matriz |
| `backend/app/capacity_observability/database.py:42` / `<módulo>` | O | query/ORM | `text` | ver matriz |
| `backend/app/capacity_observability/database.py:133` / `read_postgres_snapshot` | O | query/ORM | `settings_row.get` | ver matriz |
| `backend/app/capacity_observability/database.py:140` / `read_postgres_snapshot` | O | query/ORM | `settings_row.get` | ver matriz |
| `backend/app/capacity_observability/database.py:147` / `read_postgres_snapshot` | O | query/ORM | `settings_row.get` | ver matriz |
| `backend/app/capacity_observability/database.py:94` / `_connection_states` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/capacity_observability/queues.py:234` / `collect_adjustment_queue` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:61` / `_age` | O | efeito potencial | `timestamp.replace` | ver matriz |
| `backend/app/capacity_observability/queues.py:177` / `collect_facial_queues` | O | query/ORM | `rows.get` | ver matriz |
| `backend/app/capacity_observability/queues.py:174` / `collect_facial_queues` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/queues.py:211` / `collect_media_queue` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:218` / `collect_media_queue` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/queues.py:239` / `collect_adjustment_queue` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/queues.py:157` / `collect_facial_queues` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:199` / `collect_media_queue` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:150` / `collect_facial_queues` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:209` / `collect_media_queue` | O | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:46` / `lock_client_commerce` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:49` / `lock_client_commerce` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:50` / `lock_client_commerce` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:60` / `lock_client_commerce` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:70` / `client_photo_is_frozen` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:93` / `client_photo_is_frozen_any` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:117` / `selected_photos` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:172` / `_checkout_material` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:239` / `_checkout_material` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:256` / `_checkout_material` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:280` / `_synchronize_order` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:316` / `_synchronize_order` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/checkout.py:318` / `_synchronize_order` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:346` / `remove_canonical_cart_selection` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:353` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:354` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:378` / `remove_canonical_cart_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:381` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:407` / `create_pending_checkout` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:409` / `create_pending_checkout` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:442` / `create_pending_checkout` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:473` / `synchronize_editable_draft` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:476` / `synchronize_editable_draft` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:490` / `synchronize_editable_draft` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:493` / `synchronize_editable_draft` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:514` / `synchronize_editable_draft` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:536` / `freeze_pending_checkout` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:541` / `freeze_pending_checkout` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:562` / `freeze_pending_checkout` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:573` / `freeze_pending_checkout` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:72` / `client_photo_is_frozen` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:94` / `client_photo_is_frozen_any` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:137` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:150` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:220` / `_checkout_material` | S | query/ORM | `folders_by_id.get` | ver matriz |
| `backend/app/checkout.py:327` / `_synchronize_order` | S | query/ORM | `folders_by_id.get` | ver matriz |
| `backend/app/checkout.py:328` / `_synchronize_order` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/checkout.py:375` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:390` / `remove_canonical_cart_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:392` / `remove_canonical_cart_selection` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/checkout.py:423` / `create_pending_checkout` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:451` / `create_pending_checkout` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/checkout.py:501` / `synchronize_editable_draft` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:502` / `synchronize_editable_draft` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/checkout.py:121` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:125` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:190` / `_checkout_material` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:212` / `_checkout_material` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:329` / `_synchronize_order` | S | produtor | `SaleOrderItem` | ver matriz |
| `backend/app/checkout.py:397` / `remove_canonical_cart_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:508` / `synchronize_editable_draft` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:394` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:505` / `synchronize_editable_draft` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:146` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:360` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:213` / `_checkout_material` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:318` / `_synchronize_order` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:378` / `remove_canonical_cart_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:410` / `create_pending_checkout` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:494` / `synchronize_editable_draft` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:574` / `freeze_pending_checkout` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:138` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:390` / `remove_canonical_cart_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:501` / `synchronize_editable_draft` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:49` / `lock_client_commerce` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:51` / `lock_client_commerce` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:61` / `lock_client_commerce` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:121` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:191` / `_checkout_material` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:240` / `_checkout_material` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:353` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:354` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:381` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:397` / `remove_canonical_cart_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:477` / `synchronize_editable_draft` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:508` / `synchronize_editable_draft` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:542` / `freeze_pending_checkout` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:73` / `client_photo_is_frozen` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:95` / `client_photo_is_frozen_any` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:394` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:505` / `synchronize_editable_draft` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:151` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:424` / `create_pending_checkout` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:35` / `client_carts_by_gallery_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:105` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:176` / `client_carts_by_gallery_payload` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/client_commerce.py:185` / `client_photo_states` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:250` / `client_orders_by_gallery_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:275` / `client_orders_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:397` / `client_orders_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:50` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:74` / `client_carts_by_gallery_payload` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_commerce.py:117` / `client_carts_by_gallery_payload` | S | query/ORM | `drafts_by_gallery.get` | ver matriz |
| `backend/app/client_commerce.py:147` / `client_carts_by_gallery_payload` | S | query/ORM | `parents.get` | ver matriz |
| `backend/app/client_commerce.py:162` / `client_carts_by_gallery_payload` | S | query/ORM | `payload.update` | ver matriz |
| `backend/app/client_commerce.py:191` / `client_photo_states` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:206` / `client_photo_states` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_commerce.py:258` / `client_orders_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:303` / `client_orders_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:314` / `client_orders_by_gallery_payload` | S | query/ORM | `communications.get` | ver matriz |
| `backend/app/client_commerce.py:61` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:81` / `client_carts_by_gallery_payload` | S | query/ORM | `draft_items[order_id].add` | ver matriz |
| `backend/app/client_commerce.py:102` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:123` / `client_carts_by_gallery_payload` | S | query/ORM | `photos.get` | ver matriz |
| `backend/app/client_commerce.py:126` / `client_carts_by_gallery_payload` | S | query/ORM | `photo_media_states.get` | ver matriz |
| `backend/app/client_commerce.py:127` / `client_carts_by_gallery_payload` | S | query/ORM | `photo_expiries.get` | ver matriz |
| `backend/app/client_commerce.py:315` / `client_orders_by_gallery_payload` | S | query/ORM | `deliveries.get` | ver matriz |
| `backend/app/client_commerce.py:51` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:75` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:192` / `client_photo_states` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:368` / `client_orders_by_gallery_payload` | S | query/ORM | `media_states.get` | ver matriz |
| `backend/app/client_commerce.py:62` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:102` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:106` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:276` / `client_orders_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:259` / `client_orders_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:304` / `client_orders_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:377` / `client_orders_by_gallery_payload` | S | query/ORM | `folder_expiries.get` | ver matriz |
| `backend/app/client_commerce.py:207` / `client_photo_states` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:375` / `client_orders_by_gallery_payload` | S | query/ORM | `media_states.get` | ver matriz |
| `backend/app/client_identity.py:22` / `require_client_owner` | C | gate | `require_identity_tenant` | ver matriz |
| `backend/app/client_identity.py:30` / `resolve_client_by_phone` | C | gate | `require_identity_tenant` | ver matriz |
| `backend/app/client_identity.py:31` / `resolve_client_by_phone` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:39` / `resolve_client_by_phone` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:54` / `assert_phone_available` | C | gate | `require_identity_tenant` | ver matriz |
| `backend/app/client_identity.py:57` / `assert_phone_available` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:60` / `assert_phone_available` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:77` / `verify_canonical_phone` | C | gate | `require_client_owner` | ver matriz |
| `backend/app/client_identity.py:81` / `verify_canonical_phone` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:110` / `change_verified_phone` | C | gate | `require_client_owner` | ver matriz |
| `backend/app/client_identity.py:114` / `change_verified_phone` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:131` / `change_verified_phone` | C | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_identity.py:16` / `require_identity_tenant` | C | query/ORM | `db.get` | ver matriz |
| `backend/app/client_identity.py:45` / `resolve_client_by_phone` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:94` / `verify_canonical_phone` | C | produtor | `ClientPhone` | ver matriz |
| `backend/app/client_identity.py:100` / `verify_canonical_phone` | C | query/ORM | `db.add` | ver matriz |
| `backend/app/client_identity.py:122` / `change_verified_phone` | C | query/ORM | `db.add` | ver matriz |
| `backend/app/client_identity.py:143` / `change_verified_phone` | C | produtor | `ClientPhone` | ver matriz |
| `backend/app/client_identity.py:149` / `change_verified_phone` | C | query/ORM | `db.add` | ver matriz |
| `backend/app/client_identity.py:55` / `assert_phone_available` | C | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_identity.py:123` / `change_verified_phone` | C | produtor | `ClientPhone` | ver matriz |
| `backend/app/client_identity.py:32` / `resolve_client_by_phone` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:39` / `resolve_client_by_phone` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:57` / `assert_phone_available` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:61` / `assert_phone_available` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:82` / `verify_canonical_phone` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:115` / `change_verified_phone` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:132` / `change_verified_phone` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:45` / `resolve_client_by_phone` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_identity.py:55` / `assert_phone_available` | C | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:102` / `list_client_directory` | L | efeito potencial | `select(func.count(func.distinct(DerivedGalleryMembership.derived_gallery_id))).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').correlate(Client).scalar_subquery` | ver matriz |
| `backend/app/client_lifecycle.py:112` / `list_client_directory` | L | efeito potencial | `select(func.count(DerivedGallery.id)).where(DerivedGallery.tenant_id == tenant_id, DerivedGallery.client_id == Client.id, ~select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').exists()).correlate(Client).scalar_subquery` | ver matriz |
| `backend/app/client_lifecycle.py:210` / `deletion_inventory` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/client_lifecycle.py:370` / `delete_client_operational_graph` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/client_lifecycle.py:377` / `delete_client_operational_graph` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:387` / `delete_client_operational_graph` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:588` / `delete_client_operational_graph` | L | query/ORM | `db.delete` | ver matriz |
| `backend/app/client_lifecycle.py:591` / `delete_client_operational_graph` | L | produtor | `ClientDeletionReceipt` | ver matriz |
| `backend/app/client_lifecycle.py:602` / `delete_client_operational_graph` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/client_lifecycle.py:604` / `delete_client_operational_graph` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/client_lifecycle.py:683` / `_client_auth_phones` | L | query/ORM | `phones.add` | ver matriz |
| `backend/app/client_lifecycle.py:703` / `_shared_gallery_successor` | L | gate | `owned_record` | ver matriz |
| `backend/app/client_lifecycle.py:768` / `_delete_where` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_lifecycle.py:87` / `list_client_directory` | L | gate | `require_identity_tenant` | ver matriz |
| `backend/app/client_lifecycle.py:183` / `list_client_directory` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_lifecycle.py:296` / `deletion_inventory` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:303` / `deletion_inventory` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:396` / `delete_client_operational_graph` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:456` / `delete_client_operational_graph` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:463` / `delete_client_operational_graph` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_lifecycle.py:505` / `delete_client_operational_graph` | L | gate | `owned_record` | ver matriz |
| `backend/app/client_lifecycle.py:545` / `delete_client_operational_graph` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:605` / `delete_client_operational_graph` | L | produtor | `AuditEvent` | ver matriz |
| `backend/app/client_lifecycle.py:631` / `remove_facial_reference_files` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/client_lifecycle.py:639` / `receipt_payload` | L | efeito potencial | `completed_at.replace` | ver matriz |
| `backend/app/client_lifecycle.py:655` / `_client_gallery_ids` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:676` / `_client_auth_phones` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:707` / `_shared_gallery_successor` | L | efeito potencial | `select(DerivedGalleryMembership.client_id).where(DerivedGalleryMembership.tenant_id == tenant_id).where(DerivedGalleryMembership.derived_gallery_id == gallery_id, DerivedGalleryMembership.client_id != excluded_client_id, DerivedGalleryMembership.status != 'unlinked').order_by` | ver matriz |
| `backend/app/client_lifecycle.py:748` / `_shared_gallery_successor` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:102` / `list_client_directory` | L | efeito potencial | `select(func.count(func.distinct(DerivedGalleryMembership.derived_gallery_id))).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').correlate` | ver matriz |
| `backend/app/client_lifecycle.py:112` / `list_client_directory` | L | efeito potencial | `select(func.count(DerivedGallery.id)).where(DerivedGallery.tenant_id == tenant_id, DerivedGallery.client_id == Client.id, ~select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').exists()).correlate` | ver matriz |
| `backend/app/client_lifecycle.py:154` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:617` / `delete_client_operational_graph` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:756` / `_count` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:313` / `deletion_inventory` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:326` / `deletion_inventory` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:372` / `delete_client_operational_graph` | L | gate | `require_admin_tenant` | ver matriz |
| `backend/app/client_lifecycle.py:768` / `_delete_where` | L | query/ORM | `delete` | ver matriz |
| `backend/app/client_lifecycle.py:217` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:294` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:402` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:650` / `_client_gallery_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:378` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:480` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:720` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:724` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:728` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:732` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:736` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:740` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:92` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:102` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:112` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:116` / `list_client_directory` | L | efeito potencial | `select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').exists` | ver matriz |
| `backend/app/client_lifecycle.py:129` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:135` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:142` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:148` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:297` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:304` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:396` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:457` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:546` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:677` / `_client_auth_phones` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:387` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:618` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:707` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:714` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:464` / `delete_client_operational_graph` | L | query/ORM | `update` | ver matriz |
| `backend/app/client_lifecycle.py:656` / `_client_gallery_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:756` / `_count` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:116` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:314` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:327` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/combined_environment_transition.py:75` / `read_channel_snapshot` | X | query/ORM | `connection.execute` | ver matriz |
| `backend/app/combined_environment_transition.py:75` / `read_channel_snapshot` | X | query/ORM | `text` | ver matriz |
| `backend/app/combined_environment_transition.py:93` / `replace_channel_environment` | X | query/ORM | `connection.execute` | ver matriz |
| `backend/app/combined_environment_transition.py:76` / `read_channel_snapshot` | X | query/ORM | `connection.execute` | ver matriz |
| `backend/app/combined_environment_transition.py:93` / `replace_channel_environment` | X | query/ORM | `update` | ver matriz |
| `backend/app/combined_environment_transition.py:76` / `read_channel_snapshot` | X | query/ORM | `select` | ver matriz |
| `backend/app/commercial_history.py:54` / `materialize_commercial_history` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_history.py:72` / `materialize_commercial_history` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/commercial_history.py:73` / `materialize_commercial_history` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/commercial_history.py:208` / `backfill_commercial_snapshots` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_history.py:255` / `backfill_commercial_snapshots` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_history.py:274` / `backfill_commercial_snapshots` | S | query/ORM | `orders_by_id.get` | ver matriz |
| `backend/app/commercial_history.py:277` / `backfill_commercial_snapshots` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/commercial_history.py:68` / `materialize_commercial_history` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/commercial_history.py:123` / `materialize_commercial_history` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_history.py:139` / `materialize_commercial_history` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/commercial_history.py:218` / `backfill_commercial_snapshots` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/commercial_history.py:220` / `backfill_commercial_snapshots` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/commercial_history.py:259` / `backfill_commercial_snapshots` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/commercial_history.py:183` / `commercial_history_orders_query` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_history.py:176` / `commercial_history_orders_query` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_history.py:208` / `backfill_commercial_snapshots` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_history.py:255` / `backfill_commercial_snapshots` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_history.py:278` / `backfill_commercial_snapshots` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_history.py:124` / `materialize_commercial_history` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:64` / `build_commercial_projections` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/commercial_projection.py:84` / `build_commercial_projections` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/commercial_projection.py:87` / `build_commercial_projections` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/commercial_projection.py:162` / `build_commercial_projections` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_projection.py:85` / `build_commercial_projections` | S | query/ORM | `available_photo_ids[gallery_id].add` | ver matriz |
| `backend/app/commercial_projection.py:98` / `build_commercial_projections` | S | query/ORM | `selected_photo_ids[gallery_id, client_id].add` | ver matriz |
| `backend/app/commercial_projection.py:100` / `build_commercial_projections` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/commercial_projection.py:146` / `build_commercial_projections` | S | query/ORM | `item_ids_by_order[row.id].add` | ver matriz |
| `backend/app/commercial_projection.py:148` / `build_commercial_projections` | S | query/ORM | `pending_review_order_ids.add` | ver matriz |
| `backend/app/commercial_projection.py:150` / `build_commercial_projections` | S | query/ORM | `purchased_photo_ids[row.derived_gallery_id_snapshot, row.client_id].add` | ver matriz |
| `backend/app/commercial_projection.py:180` / `build_commercial_projections` | S | query/ORM | `available_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:183` / `build_commercial_projections` | S | query/ORM | `orders_by_key.get` | ver matriz |
| `backend/app/commercial_projection.py:196` / `build_commercial_projections` | S | query/ORM | `latest_reopening.get` | ver matriz |
| `backend/app/commercial_projection.py:72` / `build_commercial_projections` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_projection.py:158` / `build_commercial_projections` | S | query/ORM | `selected_photo_ids[row.derived_gallery_id_snapshot, row.client_id].add` | ver matriz |
| `backend/app/commercial_projection.py:79` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:88` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:205` / `build_commercial_projections` | S | query/ORM | `purchased_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:75` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:202` / `build_commercial_projections` | S | query/ORM | `selected_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:203` / `build_commercial_projections` | S | query/ORM | `purchased_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:221` / `build_commercial_projections` | S | query/ORM | `scopes.get` | ver matriz |
| `backend/app/commercial_projection.py:163` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:72` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:101` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_removal.py:86` / `apply_commercial_removal_policy` | L | gate | `owned_record` | ver matriz |
| `backend/app/commercial_removal.py:100` / `apply_commercial_removal_policy` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_removal.py:53` / `commercial_removal_orders_query` | L | query/ORM | `select` | ver matriz |
| `backend/app/commercial_removal.py:90` / `apply_commercial_removal_policy` | L | gate | `owned_record` | ver matriz |
| `backend/app/commercial_removal.py:109` / `apply_commercial_removal_policy` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_removal.py:133` / `apply_commercial_removal_policy` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/commercial_removal.py:64` / `commercial_removal_orders_query` | L | query/ORM | `select` | ver matriz |
| `backend/app/commercial_removal.py:134` / `apply_commercial_removal_policy` | L | produtor | `AuditEvent` | ver matriz |
| `backend/app/commercial_removal.py:110` / `apply_commercial_removal_policy` | L | query/ORM | `select` | ver matriz |
| `backend/app/commercial_retention.py:65` / `apply_commercial_media_retention` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/commercial_retention.py:140` / `minimize_client_commercial_pii` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_retention.py:75` / `apply_commercial_media_retention` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/commercial_retention.py:97` / `apply_commercial_media_retention` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/commercial_retention.py:136` / `minimize_client_commercial_pii` | L | gate | `owned_record` | ver matriz |
| `backend/app/commercial_retention.py:149` / `minimize_client_commercial_pii` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/commercial_retention.py:101` / `apply_commercial_media_retention` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/commercial_retention.py:150` / `minimize_client_commercial_pii` | L | produtor | `AuditEvent` | ver matriz |
| `backend/app/commercial_retention.py:103` / `apply_commercial_media_retention` | L | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/commercial_retention.py:141` / `minimize_client_commercial_pii` | L | query/ORM | `select` | ver matriz |
| `backend/app/commercial_retention.py:76` / `apply_commercial_media_retention` | L | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:132` / `history_page` | S | efeito potencial | `select(rows.c.group_key, func.sum(rows.c.delta).label('delta'), func.sum(case((rows.c.entry_type == 'upload_consumption', 1), else_=0)).label('photo_count'), func.min(rows.c.created_at).label('first_at'), func.max(rows.c.created_at).label('last_at')).group_by(rows.c.group_key).subquery` | ver matriz |
| `backend/app/credit_history.py:48` / `_uuid_text` | S | efeito potencial | `func.replace` | ver matriz |
| `backend/app/credit_history.py:113` / `_utc` | S | efeito potencial | `value.replace` | ver matriz |
| `backend/app/credit_history.py:122` / `_require_wallet` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/credit_history.py:26` / `photo_history_context` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/credit_history.py:132` / `history_page` | S | efeito potencial | `select(rows.c.group_key, func.sum(rows.c.delta).label('delta'), func.sum(case((rows.c.entry_type == 'upload_consumption', 1), else_=0)).label('photo_count'), func.min(rows.c.created_at).label('first_at'), func.max(rows.c.created_at).label('last_at')).group_by` | ver matriz |
| `backend/app/credit_history.py:139` / `history_page` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:187` / `folder_entry_page` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/credit_history.py:53` / `_history_rows` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:66` / `_history_rows` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:132` / `history_page` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:143` / `history_page` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/credit_history.py:183` / `folder_entry_page` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/credit_history.py:135` / `history_page` | S | efeito potencial | `func.sum(case((rows.c.entry_type == 'upload_consumption', 1), else_=0)).label` | ver matriz |
| `backend/app/credit_history.py:100` / `_history_rows` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:187` / `folder_entry_page` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:26` / `photo_history_context` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:143` / `history_page` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:183` / `folder_entry_page` | S | query/ORM | `select` | ver matriz |
| `backend/app/credit_history.py:69` / `_history_rows` | S | query/ORM | `select` | ver matriz |
| `backend/app/email_delivery.py:182` / `email_provider_from_environment` | N | efeito potencial | `_sender_domain` | ver matriz |
| `backend/app/email_delivery.py:275` / `enqueue_email` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/email_delivery.py:280` / `enqueue_email` | N | produtor | `EmailDelivery` | ver matriz |
| `backend/app/email_delivery.py:289` / `enqueue_email` | N | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/email_delivery.py:293` / `enqueue_email` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/email_delivery.py:89` / `send` | N | efeito potencial | `_sender_domain` | ver matriz |
| `backend/app/email_delivery.py:276` / `enqueue_email` | N | query/ORM | `select` | ver matriz |
| `backend/app/email_delivery.py:107` / `send` | N | efeito potencial | `client.send_message` | ver matriz |
| `backend/app/email_delivery.py:119` / `send` | N | efeito potencial | `client.send_message` | ver matriz |
| `backend/app/environment_transition_bundle.py:76` / `seal_payload` | X | efeito potencial | `AESGCM(key).encrypt` | ver matriz |
| `backend/app/environment_transition_bundle.py:111` / `persist_profile` | X | efeito potencial | `persist_encrypted_package` | ver matriz |
| `backend/app/environment_transition_bundle.py:161` / `prepare_bundle` | X | efeito potencial | `persist_encrypted_package` | ver matriz |
| `backend/app/environment_transition_bundle.py:79` / `seal_payload` | X | efeito potencial | `base64.b64encode(encrypted).decode` | ver matriz |
| `backend/app/environment_transition_bundle.py:97` / `assert_sql_only_idle` | X | query/ORM | `connection.scalar` | ver matriz |
| `backend/app/environment_transition_bundle.py:99` / `assert_sql_only_idle` | X | query/ORM | `connection.scalar` | ver matriz |
| `backend/app/environment_transition_bundle.py:101` / `assert_sql_only_idle` | X | query/ORM | `connection.scalar` | ver matriz |
| `backend/app/environment_transition_bundle.py:116` / `persist_profile` | X | query/ORM | `connection.scalar` | ver matriz |
| `backend/app/environment_transition_bundle.py:148` / `prepare_bundle` | X | efeito potencial | `create_encrypted_transition_backup` | ver matriz |
| `backend/app/environment_transition_bundle.py:206` / `apply_bundle` | X | efeito potencial | `persist_encrypted_package` | ver matriz |
| `backend/app/environment_transition_bundle.py:86` / `open_payload` | X | efeito potencial | `AESGCM(key).decrypt` | ver matriz |
| `backend/app/environment_transition_bundle.py:116` / `persist_profile` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_bundle.py:65` / `financial_snapshot` | X | query/ORM | `connection.execute` | ver matriz |
| `backend/app/environment_transition_bundle.py:139` / `prepare_bundle` | X | query/ORM | `connection.execute` | ver matriz |
| `backend/app/environment_transition_bundle.py:65` / `financial_snapshot` | X | query/ORM | `text` | ver matriz |
| `backend/app/environment_transition_bundle.py:97` / `assert_sql_only_idle` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_bundle.py:99` / `assert_sql_only_idle` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_bundle.py:101` / `assert_sql_only_idle` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_bundle.py:140` / `prepare_bundle` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_channels.py:51` / `inspect_channel_continuity` | N | query/ORM | `session.scalars` | ver matriz |
| `backend/app/environment_transition_channels.py:56` / `inspect_channel_continuity` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/environment_transition_channels.py:54` / `inspect_channel_continuity` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/environment_transition_channels.py:51` / `inspect_channel_continuity` | N | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_inventory.py:157` / `_whatsapp_binding_counts` | X | query/ORM | `seen.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:202` / `_service_summaries` | X | query/ORM | `seen.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:287` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:289` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:291` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:293` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:295` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:297` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:304` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:306` / `build_environment_inventory` | X | query/ORM | `blockers.add` | ver matriz |
| `backend/app/environment_transition_inventory.py:380` / `render_environment_inventory` | X | query/ORM | `seen.add` | ver matriz |
| `backend/app/environment_transition_runtime.py:41` / `eligibility_matrix` | X | query/ORM | `session.scalars` | ver matriz |
| `backend/app/environment_transition_runtime.py:46` / `eligibility_matrix` | X | query/ORM | `session.scalars` | ver matriz |
| `backend/app/environment_transition_runtime.py:86` / `require_reference_store_empty` | X | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/environment_transition_runtime.py:41` / `eligibility_matrix` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_runtime.py:42` / `eligibility_matrix` | X | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/environment_transition_runtime.py:44` / `eligibility_matrix` | X | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/environment_transition_runtime.py:46` / `eligibility_matrix` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_runtime.py:50` / `eligibility_matrix` | X | query/ORM | `session.scalar` | ver matriz |
| `backend/app/environment_transition_runtime.py:110` / `run_runtime` | X | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/environment_transition_runtime.py:111` / `run_runtime` | X | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/environment_transition_runtime.py:92` / `preservation_metadata_verified` | X | query/ORM | `connection.execute` | ver matriz |
| `backend/app/environment_transition_runtime.py:128` / `run_runtime` | X | query/ORM | `connection.execute(text('SELECT version_num FROM alembic_version')).scalars` | ver matriz |
| `backend/app/environment_transition_runtime.py:50` / `eligibility_matrix` | X | query/ORM | `select` | ver matriz |
| `backend/app/environment_transition_runtime.py:92` / `preservation_metadata_verified` | X | query/ORM | `text` | ver matriz |
| `backend/app/environment_transition_runtime.py:63` / `eligibility_matrix` | X | query/ORM | `session.scalar` | ver matriz |
| `backend/app/environment_transition_runtime.py:128` / `run_runtime` | X | query/ORM | `connection.execute` | ver matriz |
| `backend/app/environment_transition_runtime.py:128` / `run_runtime` | X | query/ORM | `text` | ver matriz |
| `backend/app/environment_transition_runtime.py:63` / `eligibility_matrix` | X | query/ORM | `select` | ver matriz |
| `backend/app/facial/analysis_metrics.py:42` / `gallery_analysis_metrics` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/analysis_metrics.py:49` / `gallery_analysis_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/analysis_metrics.py:64` / `gallery_analysis_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/analysis_metrics.py:62` / `gallery_analysis_metrics` | F | query/ORM | `metrics.get` | ver matriz |
| `backend/app/facial/analysis_metrics.py:74` / `gallery_analysis_metrics` | F | efeito potencial | `date.replace` | ver matriz |
| `backend/app/facial/analysis_metrics.py:50` / `gallery_analysis_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/analysis_metrics.py:65` / `gallery_analysis_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/calibration.py:44` / `approve_calibration` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/calibration.py:58` / `approve_calibration` | F | produtor | `FacialCalibrationApproval` | ver matriz |
| `backend/app/facial/calibration.py:73` / `approve_calibration` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/calibration.py:75` / `approve_calibration` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/calibration.py:91` / `calibration_is_approved` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/calibration.py:34` / `approve_calibration` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/calibration.py:42` / `approve_calibration` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/calibration.py:76` / `approve_calibration` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/calibration.py:95` / `calibration_is_approved` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/calibration.py:45` / `approve_calibration` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/calibration.py:96` / `calibration_is_approved` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/capacity.py:42` / `measure_search_queue` | F | efeito potencial | `current.replace` | ver matriz |
| `backend/app/facial/capacity.py:44` / `measure_search_queue` | F | efeito potencial | `oldest.replace` | ver matriz |
| `backend/app/facial/capacity.py:34` / `measure_search_queue` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/capacity.py:35` / `measure_search_queue` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_cleanup.py:202` / `_cancel_unclaimed_and_expired_work` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/closure_cleanup.py:220` / `_cancel_unclaimed_and_expired_work` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/closure_cleanup.py:236` / `_cancel_unclaimed_and_expired_work` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/closure_cleanup.py:59` / `cleanup_tenant_biometrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/closure_cleanup.py:68` / `cleanup_tenant_biometrics` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/closure_cleanup.py:82` / `cleanup_tenant_biometrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/closure_cleanup.py:90` / `cleanup_tenant_biometrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/closure_cleanup.py:69` / `cleanup_tenant_biometrics` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/closure_cleanup.py:181` / `cleanup_tenant_biometrics` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/closure_cleanup.py:127` / `cleanup_tenant_biometrics` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/closure_cleanup.py:159` / `cleanup_tenant_biometrics` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/closure_cleanup.py:176` / `cleanup_tenant_biometrics` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/closure_cleanup.py:182` / `cleanup_tenant_biometrics` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/closure_cleanup.py:260` / `_operational_rows_remaining` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/closure_cleanup.py:107` / `cleanup_tenant_biometrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/closure_cleanup.py:120` / `cleanup_tenant_biometrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/closure_cleanup.py:153` / `cleanup_tenant_biometrics` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/closure_cleanup.py:128` / `cleanup_tenant_biometrics` | F | produtor | `FacialSearchConsentProof` | ver matriz |
| `backend/app/facial/closure_cleanup.py:60` / `cleanup_tenant_biometrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_cleanup.py:83` / `cleanup_tenant_biometrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_cleanup.py:91` / `cleanup_tenant_biometrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_cleanup.py:160` / `cleanup_tenant_biometrics` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/closure_cleanup.py:176` / `cleanup_tenant_biometrics` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/closure_cleanup.py:121` / `cleanup_tenant_biometrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_cleanup.py:154` / `cleanup_tenant_biometrics` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/closure_cleanup.py:203` / `_cancel_unclaimed_and_expired_work` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/closure_cleanup.py:221` / `_cancel_unclaimed_and_expired_work` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/closure_cleanup.py:237` / `_cancel_unclaimed_and_expired_work` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/closure_cleanup.py:261` / `_operational_rows_remaining` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_cleanup.py:108` / `cleanup_tenant_biometrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_gate.py:27` / `lock_facial_tenant` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/closure_gate.py:31` / `biometric_cleanup_started` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/closure_gate.py:22` / `lock_facial_tenant` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/closure_gate.py:32` / `biometric_cleanup_started` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/crypto.py:105` / `encrypt` | F | efeito potencial | `AESGCM(self._keys[self._active_key_id]).encrypt` | ver matriz |
| `backend/app/facial/crypto.py:117` / `decrypt` | F | query/ORM | `self._keys.get` | ver matriz |
| `backend/app/facial/crypto.py:134` / `rotate` | F | efeito potencial | `self.decrypt` | ver matriz |
| `backend/app/facial/crypto.py:137` / `rotate` | F | efeito potencial | `self.encrypt` | ver matriz |
| `backend/app/facial/crypto.py:121` / `decrypt` | F | efeito potencial | `AESGCM(key).decrypt` | ver matriz |
| `backend/app/facial/engine.py:64` / `replace_photo_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:72` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:81` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:91` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:108` / `replace_photo_index` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/engine.py:110` / `replace_photo_index` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/engine.py:118` / `revalidate` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:119` / `revalidate` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:120` / `revalidate` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:150` / `replace_photo_index` | F | efeito potencial | `json.dumps({'embedding': face.embedding, 'quality': assessment.encrypted_indicators()}, separators=(',', ':'), sort_keys=True).encode` | ver matriz |
| `backend/app/facial/engine.py:158` / `replace_photo_index` | F | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/facial/engine.py:199` / `replace_photo_index` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/engine.py:207` / `replace_photo_index` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/engine.py:241` / `search_gallery_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:176` / `replace_photo_index` | F | produtor | `PhotoFaceEmbedding` | ver matriz |
| `backend/app/facial/engine.py:330` / `search_gallery_index` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/engine.py:363` / `search_gallery_index` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/engine.py:384` / `search_gallery_index` | F | query/ORM | `best_by_photo.get` | ver matriz |
| `backend/app/facial/engine.py:73` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:82` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:92` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:347` / `search_gallery_index` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/engine.py:200` / `replace_photo_index` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/engine.py:343` / `search_gallery_index` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/engine.py:354` / `search_gallery_index` | F | query/ORM | `allowed_fingerprints.get` | ver matriz |
| `backend/app/facial/engine.py:153` / `replace_photo_index` | F | efeito potencial | `assessment.encrypted_indicators` | ver matriz |
| `backend/app/facial/engine.py:120` / `revalidate` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:248` / `search_gallery_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:287` / `search_gallery_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/environment_backup.py:136` / `create_encrypted_biometric_backup` | F | efeito potencial | `AESGCM(backup_key).encrypt` | ver matriz |
| `backend/app/facial/environment_backup.py:183` / `restore_encrypted_biometric_backup` | F | efeito potencial | `AESGCM(backup_key).decrypt` | ver matriz |
| `backend/app/facial/environment_eligibility.py:108` / `classify_biometric_evidence` | F | query/ORM | `_EXPECTED_PURPOSE.get` | ver matriz |
| `backend/app/facial/environment_eligibility.py:219` / `_as_utc` | F | efeito potencial | `value.replace` | ver matriz |
| `backend/app/facial/environment_migration.py:86` / `reencrypt_eligible_record` | F | query/ORM | `_OBJECT_KINDS.get` | ver matriz |
| `backend/app/facial/environment_migration.py:110` / `reencrypt_eligible_record` | F | efeito potencial | `contexts.source.cipher.decrypt` | ver matriz |
| `backend/app/facial/environment_migration.py:113` / `reencrypt_eligible_record` | F | efeito potencial | `contexts.destination.cipher.encrypt` | ver matriz |
| `backend/app/facial/environment_origin.py:64` / `inspect_embedding_origins` | F | query/ORM | `connection.execute` | ver matriz |
| `backend/app/facial/environment_origin.py:24` / `inspect_embedding_origins` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/environment_origin.py:32` / `inspect_embedding_origins` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/environment_origin.py:43` / `inspect_embedding_origins` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/environment_origin.py:64` / `inspect_embedding_origins` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/environment_package_store.py:33` / `_directory` | F | efeito potencial | `os.open` | ver matriz |
| `backend/app/facial/environment_package_store.py:51` / `_read` | F | efeito potencial | `os.open` | ver matriz |
| `backend/app/facial/environment_package_store.py:65` / `_write` | F | efeito potencial | `os.open` | ver matriz |
| `backend/app/facial/environment_package_store.py:108` / `persist_encrypted_package` | F | efeito potencial | `json.dumps(encrypted_payload, sort_keys=True, allow_nan=False).encode` | ver matriz |
| `backend/app/facial/environment_package_store.py:38` / `_directory` | F | efeito potencial | `os.open` | ver matriz |
| `backend/app/facial/environment_sql.py:47` / `lock_embedding_snapshot` | F | query/ORM | `connection.execute` | ver matriz |
| `backend/app/facial/environment_sql.py:48` / `lock_embedding_snapshot` | F | query/ORM | `connection.execute` | ver matriz |
| `backend/app/facial/environment_sql.py:47` / `lock_embedding_snapshot` | F | query/ORM | `text` | ver matriz |
| `backend/app/facial/environment_sql.py:48` / `lock_embedding_snapshot` | F | query/ORM | `text` | ver matriz |
| `backend/app/facial/environment_sql.py:68` / `prepare_embedding_destination` | F | query/ORM | `seen.add` | ver matriz |
| `backend/app/facial/environment_sql.py:75` / `prepare_embedding_destination` | F | efeito potencial | `contexts.source.cipher.decrypt` | ver matriz |
| `backend/app/facial/environment_sql.py:77` / `prepare_embedding_destination` | F | efeito potencial | `contexts.destination.cipher.encrypt` | ver matriz |
| `backend/app/facial/environment_sql.py:78` / `prepare_embedding_destination` | F | efeito potencial | `contexts.destination.cipher.decrypt` | ver matriz |
| `backend/app/facial/environment_sql.py:119` / `replace_embedding_envelopes` | F | query/ORM | `connection.execute` | ver matriz |
| `backend/app/facial/environment_sql.py:49` / `lock_embedding_snapshot` | F | query/ORM | `connection.execute` | ver matriz |
| `backend/app/facial/environment_sql.py:50` / `lock_embedding_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/environment_sql.py:119` / `replace_embedding_envelopes` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/environment_sql_backup.py:133` / `seal_sql_transition` | F | efeito potencial | `AESGCM(backup_key).encrypt` | ver matriz |
| `backend/app/facial/environment_sql_backup.py:144` / `_open_sql_archive` | F | efeito potencial | `AESGCM(backup_key).decrypt` | ver matriz |
| `backend/app/facial/environment_sql_backup.py:118` / `_validate_pair` | F | efeito potencial | `context.cipher.decrypt` | ver matriz |
| `backend/app/facial/environment_sql_backup.py:193` / `inspect_sql_destination` | F | query/ORM | `connection.execute` | ver matriz |
| `backend/app/facial/environment_sql_backup.py:194` / `inspect_sql_destination` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/face_worker.py:59` / `record_provider_failure` | F | gate | `domain_session` | ver matriz |
| `backend/app/facial/face_worker.py:95` / `main` | F | gate | `domain_session` | ver matriz |
| `backend/app/facial/face_worker.py:148` / `processor` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/indexing.py:110` / `enqueue_photo_index_if_eligible` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/indexing.py:138` / `enqueue_photo_index_if_eligible` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/indexing.py:203` / `enqueue_gallery_backfill_page` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/indexing.py:239` / `enqueue_gallery_backfill_page` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/indexing.py:252` / `enqueue_gallery_backfill_page` | F | efeito potencial | `enqueue_photo_index_if_eligible` | ver matriz |
| `backend/app/facial/indexing.py:289` / `reconcile_gallery_index` | F | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/facial/indexing.py:324` / `reconcile_automatic_gallery_policies` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/indexing.py:66` / `preview_fingerprint` | F | efeito potencial | `path.open` | ver matriz |
| `backend/app/facial/indexing.py:156` / `enqueue_photo_index_if_eligible` | F | efeito potencial | `(repository or FacialJobRepository()).enqueue` | ver matriz |
| `backend/app/facial/indexing.py:367` / `reconcile_automatic_gallery_policies` | F | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/facial/indexing.py:68` / `preview_fingerprint` | F | query/ORM | `digest.update` | ver matriz |
| `backend/app/facial/indexing.py:139` / `enqueue_photo_index_if_eligible` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/indexing.py:325` / `reconcile_automatic_gallery_policies` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/indexing.py:209` / `enqueue_gallery_backfill_page` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/indexing.py:329` / `reconcile_automatic_gallery_policies` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:126` / `enqueue` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:131` / `enqueue` | F | produtor | `FacialJob` | ver matriz |
| `backend/app/facial/jobs.py:354` / `_leased` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/jobs.py:355` / `_leased` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:376` / `release_denied` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:399` / `dispatch` | F | efeito potencial | `self._repository.enqueue` | ver matriz |
| `backend/app/facial/jobs.py:189` / `claim_next` | F | query/ORM | `FACIAL_JOB_KINDS_BY_CLASS.get` | ver matriz |
| `backend/app/facial/jobs.py:212` / `claim_next` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:343` / `require_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/jobs.py:148` / `enqueue` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/jobs.py:151` / `enqueue` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:193` / `claim_next` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/jobs.py:348` / `require_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/jobs.py:127` / `enqueue` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:205` / `claim_next` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:175` / `claim_next` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:152` / `enqueue` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:376` / `release_denied` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:180` / `claim_next` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:406` / `dispatch` | F | query/ORM | `job.get` | ver matriz |
| `backend/app/facial/jobs.py:356` / `_leased` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:44` / `analysis_for` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/lifecycle.py:48` / `analysis_for` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:53` / `admit_source` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/lifecycle.py:104` / `admit_source` | F | produtor | `PhotoAnalysis` | ver matriz |
| `backend/app/facial/lifecycle.py:119` / `admit_source` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/lifecycle.py:183` / `finalize_source` | F | efeito potencial | `FacialJobRepository().enqueue` | ver matriz |
| `backend/app/facial/lifecycle.py:201` / `write_source` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/lifecycle.py:229` / `media_can_proceed` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:251` / `cleanup_source` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/lifecycle.py:254` / `cleanup_source` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:297` / `cleanup_source` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/lifecycle.py:298` / `cleanup_source` | F | efeito potencial | `safe_source_path(photo).unlink` | ver matriz |
| `backend/app/facial/lifecycle.py:342` / `cleanup_sources` | F | efeito potencial | `cleanup_upload_fragments` | ver matriz |
| `backend/app/facial/lifecycle.py:354` / `cleanup_upload_fragments` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/lifecycle.py:66` / `admit_source` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:78` / `admit_source` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/lifecycle.py:97` / `admit_source` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/lifecycle.py:163` / `source_job_key` | F | efeito potencial | `row.expires_at.replace` | ver matriz |
| `backend/app/facial/lifecycle.py:217` / `write_source` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/lifecycle.py:218` / `write_source` | F | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/facial/lifecycle.py:220` / `write_source` | F | efeito potencial | `temporary.unlink` | ver matriz |
| `backend/app/facial/lifecycle.py:267` / `cleanup_source` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/lifecycle.py:287` / `cleanup_source` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/lifecycle.py:306` / `cleanup_sources` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/lifecycle.py:45` / `analysis_for` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:78` / `admit_source` | F | query/ORM | `text` | ver matriz |
| `backend/app/facial/lifecycle.py:129` / `_require_source_capacity` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:134` / `_require_source_capacity` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/lifecycle.py:135` / `_require_source_capacity` | F | efeito potencial | `(root / '.pyp-uploading').glob` | ver matriz |
| `backend/app/facial/lifecycle.py:212` / `write_source` | F | efeito potencial | `temporary.open` | ver matriz |
| `backend/app/facial/lifecycle.py:358` / `cleanup_upload_fragments` | F | gate | `require_single_tenant` | ver matriz |
| `backend/app/facial/lifecycle.py:373` / `cleanup_upload_fragments` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/lifecycle.py:378` / `cleanup_upload_fragments` | F | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/facial/lifecycle.py:255` / `cleanup_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:285` / `cleanup_source` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/lifecycle.py:354` / `cleanup_upload_fragments` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:377` / `cleanup_upload_fragments` | F | gate | `require_single_tenant` | ver matriz |
| `backend/app/facial/lifecycle.py:66` / `admit_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:268` / `cleanup_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:374` / `cleanup_upload_fragments` | F | efeito potencial | `(root / '.pyp-uploading').resolve` | ver matriz |
| `backend/app/facial/lifecycle.py:230` / `media_can_proceed` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:307` / `cleanup_sources` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/model_assets.py:47` / `normalize_architecture` | F | query/ORM | `aliases.get` | ver matriz |
| `backend/app/facial/model_assets.py:86` / `load_manifest` | F | query/ORM | `manifest.get` | ver matriz |
| `backend/app/facial/model_assets.py:175` / `prepare_models` | F | efeito potencial | `marker_path.write_text` | ver matriz |
| `backend/app/facial/model_assets.py:55` / `sha256_file` | F | efeito potencial | `path.open` | ver matriz |
| `backend/app/facial/model_assets.py:77` / `load_manifest` | F | query/ORM | `manifest.get` | ver matriz |
| `backend/app/facial/model_assets.py:90` / `load_manifest` | F | query/ORM | `expected.get` | ver matriz |
| `backend/app/facial/model_assets.py:110` / `_read_marker` | F | query/ORM | `marker.get` | ver matriz |
| `backend/app/facial/model_assets.py:133` / `verify_models` | F | query/ORM | `marker.get` | ver matriz |
| `backend/app/facial/model_assets.py:135` / `verify_models` | F | query/ORM | `marker.get` | ver matriz |
| `backend/app/facial/model_assets.py:57` / `sha256_file` | F | query/ORM | `digest.update` | ver matriz |
| `backend/app/facial/model_assets.py:81` / `load_manifest` | F | query/ORM | `manifest.get` | ver matriz |
| `backend/app/facial/model_assets.py:95` / `load_manifest` | F | query/ORM | `expected.get` | ver matriz |
| `backend/app/facial/model_assets.py:171` / `prepare_models` | F | efeito potencial | `os.replace` | ver matriz |
| `backend/app/facial/model_assets.py:173` / `prepare_models` | F | efeito potencial | `partial.unlink` | ver matriz |
| `backend/app/facial/model_assets.py:79` / `load_manifest` | F | query/ORM | `manifest.get` | ver matriz |
| `backend/app/facial/model_assets.py:168` / `prepare_models` | F | efeito potencial | `partial.open` | ver matriz |
| `backend/app/facial/model_assets.py:169` / `prepare_models` | F | efeito potencial | `shutil.copyfileobj` | ver matriz |
| `backend/app/facial/model_assets.py:93` / `load_manifest` | F | query/ORM | `expected.get` | ver matriz |
| `backend/app/facial/model_assets.py:97` / `load_manifest` | F | query/ORM | `expected.get` | ver matriz |
| `backend/app/facial/model_assets.py:99` / `load_manifest` | F | query/ORM | `expected.get` | ver matriz |
| `backend/app/facial/notifications.py:47` / `enqueue_search_notification` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:54` / `enqueue_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:70` / `enqueue_search_notification` | F | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/facial/notifications.py:74` / `enqueue_search_notification` | F | produtor | `FacialSearchNotificationOutbox` | ver matriz |
| `backend/app/facial/notifications.py:285` / `notification_origin` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:286` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:287` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:288` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:289` / `notification_origin` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:304` / `cancel_pending_search_notifications` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:305` / `cancel_pending_search_notifications` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/notifications.py:48` / `enqueue_search_notification` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:131` / `process_next_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:184` / `process_next_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:212` / `process_next_search_notification` | F | gate | `provider_for` | ver matriz |
| `backend/app/facial/notifications.py:225` / `process_next_search_notification` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:226` / `process_next_search_notification` | F | efeito potencial | `active_provider.send_transactional` | ver matriz |
| `backend/app/facial/notifications.py:88` / `enqueue_search_notification` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/notifications.py:91` / `enqueue_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:110` / `process_next_search_notification` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/notifications.py:158` / `process_next_search_notification` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/notifications.py:331` / `_notification_message` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/notifications.py:55` / `enqueue_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:289` / `notification_origin` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:306` / `cancel_pending_search_notifications` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:153` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:92` / `enqueue_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:132` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:185` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:111` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:159` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:178` / `_utc` | F | efeito potencial | `value.replace` | ver matriz |
| `backend/app/facial/observability.py:233` / `collect_facial_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/observability.py:301` / `collect_facial_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/observability.py:233` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:320` / `collect_facial_metrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/observability.py:331` / `collect_facial_metrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/observability.py:302` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:321` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:332` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/policy.py:45` / `read_policy` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/policy.py:69` / `ensure_automatic_policy` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/policy.py:114` / `ensure_automatic_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:137` / `prepare_policy` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/policy.py:167` / `prepare_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:227` / `activate_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:43` / `read_policy` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/policy.py:88` / `ensure_automatic_policy` | F | produtor | `GalleryFacialPolicy` | ver matriz |
| `backend/app/facial/policy.py:97` / `ensure_automatic_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:115` / `ensure_automatic_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:135` / `prepare_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:145` / `prepare_policy` | F | produtor | `GalleryFacialPolicy` | ver matriz |
| `backend/app/facial/policy.py:152` / `prepare_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:161` / `prepare_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:168` / `prepare_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:212` / `activate_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:228` / `activate_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:247` / `suspend_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:257` / `suspend_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:263` / `suspend_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:280` / `revoke_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:290` / `revoke_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:296` / `revoke_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:100` / `ensure_automatic_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:264` / `suspend_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:297` / `revoke_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:46` / `read_policy` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/provider.py:222` / `observe_highres_path` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/provider.py:289` / `observe_highres_path` | F | query/ORM | `self.last_metrics.update` | ver matriz |
| `backend/app/facial/provider.py:294` / `observe_highres_path` | F | query/ORM | `self.last_metrics.update` | ver matriz |
| `backend/app/facial/purge.py:53` / `invalidate_gallery_searches` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:68` / `invalidate_gallery_searches` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:73` / `invalidate_gallery_searches` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:86` / `invalidate_gallery_searches` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:109` / `invalidate_gallery_searches` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/purge.py:163` / `reconcile_invalid_facial_records` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/purge.py:208` / `enqueue_gallery_purge` | F | efeito potencial | `(repository or FacialJobRepository()).enqueue` | ver matriz |
| `backend/app/facial/purge.py:229` / `enqueue_photo_purge` | F | efeito potencial | `(repository or FacialJobRepository()).enqueue` | ver matriz |
| `backend/app/facial/purge.py:249` / `purge_photo_records` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/purge.py:252` / `purge_photo_records` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/purge.py:255` / `purge_photo_records` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:279` / `purge_photo_records` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/purge.py:303` / `purge_gallery_records` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:347` / `purge_gallery_records` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:362` / `purge_gallery_records` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:366` / `purge_gallery_records` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:388` / `purge_gallery_records` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/purge.py:404` / `_cancel_and_detach_jobs` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/purge.py:408` / `_cancel_and_detach_jobs` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:421` / `_cancel_and_detach_jobs` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:425` / `_cancel_and_detach_jobs` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:435` / `_delete_count` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/purge.py:50` / `invalidate_gallery_searches` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/purge.py:110` / `invalidate_gallery_searches` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/purge.py:125` / `facial_cleanup_proof` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/purge.py:280` / `purge_photo_records` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/purge.py:300` / `purge_gallery_records` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/purge.py:333` / `purge_gallery_records` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/purge.py:345` / `purge_gallery_records` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/purge.py:389` / `purge_gallery_records` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/purge.py:164` / `reconcile_invalid_facial_records` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:167` / `reconcile_invalid_facial_records` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:168` / `reconcile_invalid_facial_records` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:129` / `count` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/purge.py:334` / `purge_gallery_records` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:69` / `invalidate_gallery_searches` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/purge.py:255` / `purge_photo_records` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:362` / `purge_gallery_records` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:421` / `_cancel_and_detach_jobs` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:436` / `_delete_count` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/purge.py:169` / `reconcile_invalid_facial_records` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:54` / `invalidate_gallery_searches` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:74` / `invalidate_gallery_searches` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:87` / `invalidate_gallery_searches` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:257` / `purge_photo_records` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:304` / `purge_gallery_records` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:348` / `purge_gallery_records` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:367` / `purge_gallery_records` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:409` / `_cancel_and_detach_jobs` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:422` / `_cancel_and_detach_jobs` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:426` / `_cancel_and_detach_jobs` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/purge.py:129` / `count` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/purge.py:173` / `reconcile_invalid_facial_records` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/reference.py:248` / `observe_reference_image` | F | query/ORM | `metrics.update` | ver matriz |
| `backend/app/facial/reference.py:256` / `observe_reference_image` | F | query/ORM | `metrics.update` | ver matriz |
| `backend/app/facial/reference.py:68` / `decode_reference_bytes` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/reference_store.py:118` / `store` | F | efeito potencial | `self._cipher.encrypt` | ver matriz |
| `backend/app/facial/reference_store.py:119` / `store` | F | efeito potencial | `self._cipher.encrypt` | ver matriz |
| `backend/app/facial/reference_store.py:43` / `delete_reference_file` | F | efeito potencial | `target.unlink` | ver matriz |
| `backend/app/facial/reference_store.py:133` / `store` | F | efeito potencial | `partial.write_bytes` | ver matriz |
| `backend/app/facial/reference_store.py:137` / `store` | F | efeito potencial | `os.replace` | ver matriz |
| `backend/app/facial/reference_store.py:141` / `store` | F | efeito potencial | `partial.unlink` | ver matriz |
| `backend/app/facial/reference_store.py:185` / `load` | F | efeito potencial | `self._cipher.decrypt` | ver matriz |
| `backend/app/facial/reference_store.py:211` / `delete` | F | efeito potencial | `target.unlink` | ver matriz |
| `backend/app/facial/reference_store.py:268` / `_resolve_locator` | F | efeito potencial | `self._cipher.decrypt(locator, scope=scope).decode` | ver matriz |
| `backend/app/facial/reference_store.py:224` / `_validate_jpeg` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/reference_store.py:268` / `_resolve_locator` | F | efeito potencial | `self._cipher.decrypt` | ver matriz |
| `backend/app/facial/regions.py:61` / `authorized_region` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:63` / `authorized_region` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/regions.py:78` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:81` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:82` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:88` / `region_embedding` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/regions.py:104` / `photo_regions` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:112` / `photo_regions` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/regions.py:108` / `photo_regions` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:46` / `region_query` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/regions.py:23` / `region_query` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/representation.py:80` / `create_legal_representation` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/representation.py:87` / `create_legal_representation` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/representation.py:90` / `create_legal_representation` | F | produtor | `FacialLegalRepresentation` | ver matriz |
| `backend/app/facial/representation.py:109` / `create_legal_representation` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/representation.py:111` / `create_legal_representation` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/representation.py:133` / `require_valid_legal_representation` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/representation.py:141` / `require_valid_legal_representation` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/representation.py:176` / `find_valid_legal_representation` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/representation.py:180` / `find_valid_legal_representation` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/representation.py:215` / `revoke_legal_representation` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/representation.py:239` / `legal_representation_rights_inventory` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/representation.py:287` / `fulfill_legal_representation_deletion` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/representation.py:382` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/representation.py:68` / `create_legal_representation` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/representation.py:69` / `create_legal_representation` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/representation.py:78` / `create_legal_representation` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/representation.py:112` / `create_legal_representation` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/representation.py:134` / `require_valid_legal_representation` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/representation.py:177` / `find_valid_legal_representation` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/representation.py:214` / `revoke_legal_representation` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/representation.py:222` / `revoke_legal_representation` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/representation.py:286` / `fulfill_legal_representation_deletion` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/representation.py:292` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/representation.py:314` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/representation.py:320` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/representation.py:335` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/representation.py:350` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/representation.py:359` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/representation.py:383` / `fulfill_legal_representation_deletion` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/representation.py:216` / `revoke_legal_representation` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/representation.py:223` / `revoke_legal_representation` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/representation.py:243` / `legal_representation_rights_inventory` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/representation.py:288` / `fulfill_legal_representation_deletion` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/representation.py:81` / `create_legal_representation` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/representation.py:249` / `count` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/representation.py:293` / `fulfill_legal_representation_deletion` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/representation.py:305` / `fulfill_legal_representation_deletion` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/representation.py:315` / `fulfill_legal_representation_deletion` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/representation.py:321` / `fulfill_legal_representation_deletion` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/representation.py:336` / `fulfill_legal_representation_deletion` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/representation.py:351` / `fulfill_legal_representation_deletion` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/representation.py:360` / `fulfill_legal_representation_deletion` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/representation.py:142` / `require_valid_legal_representation` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/representation.py:249` / `count` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/representation.py:181` / `find_valid_legal_representation` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/retention.py:37` / `process_claimed_cleanup_job` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/retention.py:87` / `process_claimed_cleanup_job` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/retention.py:147` / `_delete_reference` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/retention.py:96` / `process_claimed_cleanup_job` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/retention.py:109` / `process_claimed_cleanup_job` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/retention.py:165` / `_utc` | F | efeito potencial | `value.replace` | ver matriz |
| `backend/app/facial/retention.py:64` / `process_claimed_cleanup_job` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/retention.py:75` / `process_claimed_cleanup_job` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/retention.py:97` / `process_claimed_cleanup_job` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/retention.py:88` / `process_claimed_cleanup_job` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/retention.py:110` / `process_claimed_cleanup_job` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/retention.py:65` / `process_claimed_cleanup_job` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/retention.py:76` / `process_claimed_cleanup_job` | F | query/ORM | `update` | ver matriz |
| `backend/app/facial/rollout.py:38` / `calibration_allows_processing` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/rollout.py:83` / `read_rollout` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/rollout.py:96` / `prepare_rollout` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/rollout.py:266` / `rollout_is_active` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/rollout.py:335` / `canonical_rollout_environment` | F | query/ORM | `ROLLOUT_ENVIRONMENT_ALIASES.get` | ver matriz |
| `backend/app/facial/rollout.py:352` / `_schedule_scope_shutdown` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/rollout.py:378` / `_audit` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout.py:74` / `read_rollout` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/rollout.py:111` / `prepare_rollout` | F | produtor | `FacialRollout` | ver matriz |
| `backend/app/facial/rollout.py:119` / `prepare_rollout` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout.py:151` / `activate_rollout` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout.py:165` / `activate_rollout` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/rollout.py:209` / `suspend_rollout` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout.py:236` / `revoke_rollout` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout.py:279` / `rollout_is_active` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/rollout.py:379` / `_audit` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/rollout.py:76` / `read_rollout` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/rollout.py:280` / `rollout_is_active` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/rollout_operation.py:110` / `execute_protected_rollout_operation` | F | produtor | `FacialRolloutOperation` | ver matriz |
| `backend/app/facial/rollout_operation.py:123` / `execute_protected_rollout_operation` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout_operation.py:171` / `execute_protected_rollout_operation` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout_operation.py:100` / `execute_protected_rollout_operation` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/rollout_operation.py:105` / `execute_protected_rollout_operation` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout_operation.py:172` / `execute_protected_rollout_operation` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/rollout_operation.py:107` / `execute_protected_rollout_operation` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search.py:205` / `create_search_request` | F | produtor | `FacialSearchRequest` | ver matriz |
| `backend/app/facial/search.py:350` / `_build_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:529` / `read_latest_search_result` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:603` / `cancel_search_request` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search.py:608` / `cancel_search_request` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:648` / `reject_search_candidate` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:692` / `authorize_search_candidate_selection` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:736` / `_authorized_search_request` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:73` / `_require_search_context` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/search.py:243` / `create_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:267` / `create_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:268` / `create_search_request` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/search.py:271` / `create_search_request` | F | efeito potencial | `job_repository.enqueue` | ver matriz |
| `backend/app/facial/search.py:281` / `create_search_request` | F | efeito potencial | `job_repository.enqueue` | ver matriz |
| `backend/app/facial/search.py:291` / `create_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:332` / `_build_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:367` / `_build_snapshot` | F | produtor | `FacialSearchSnapshotItem` | ver matriz |
| `backend/app/facial/search.py:401` / `_retire_prior_searches` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:428` / `_retire_prior_searches` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search.py:433` / `_retire_prior_searches` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:443` / `_retire_prior_searches` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:501` / `read_search_result` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:588` / `cancel_search_request` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:619` / `cancel_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:661` / `reject_search_candidate` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:292` / `create_search_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:413` / `_retire_prior_searches` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:444` / `_retire_prior_searches` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:476` / `search_request_payload` | F | query/ORM | `_POLL_AFTER_MS.get` | ver matriz |
| `backend/app/facial/search.py:620` / `cancel_search_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:662` / `reject_search_candidate` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:307` / `create_search_request` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:604` / `cancel_search_request` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search.py:609` / `cancel_search_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:649` / `reject_search_candidate` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:693` / `authorize_search_candidate_selection` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:402` / `_retire_prior_searches` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:429` / `_retire_prior_searches` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search.py:434` / `_retire_prior_searches` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:351` / `_build_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:502` / `read_search_result` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:375` / `_build_snapshot` | F | query/ORM | `latest_by_photo.get` | ver matriz |
| `backend/app/facial/search.py:737` / `_authorized_search_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:530` / `read_latest_search_result` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:73` / `process_claimed_search_job` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:348` / `_request_is_authorized` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/search_worker.py:382` / `_request_is_authorized` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search_worker.py:527` / `_snapshot_items` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:564` / `_delete_reference` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search_worker.py:586` / `_finish_request` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/search_worker.py:604` / `_finish_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search_worker.py:614` / `_finish_request` | F | efeito potencial | `enqueue_search_notification` | ver matriz |
| `backend/app/facial/search_worker.py:218` / `process_claimed_search_job` | F | query/ORM, efeito potencial | `{'upload': settings.reference_ambiguous_threshold_milli, 'indexed_region': settings.region_ambiguous_threshold_milli}.get` | ver matriz |
| `backend/app/facial/search_worker.py:264` / `process_claimed_search_job` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search_worker.py:273` / `process_claimed_search_job` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/search_worker.py:438` / `_refresh_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:506` / `_comparison_photo_is_current` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search_worker.py:531` / `_snapshot_items` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:588` / `_finish_request` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search_worker.py:595` / `_finish_request` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search_worker.py:605` / `_finish_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search_worker.py:209` / `authorize_comparison` | F | efeito potencial | `publish_progress` | ver matriz |
| `backend/app/facial/search_worker.py:288` / `process_claimed_search_job` | F | efeito potencial | `repository.enqueue` | ver matriz |
| `backend/app/facial/search_worker.py:316` / `process_claimed_search_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/search_worker.py:328` / `process_claimed_search_job` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:418` / `_refresh_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:456` / `_refresh_snapshot` | F | query/ORM | `latest_by_photo.get` | ver matriz |
| `backend/app/facial/search_worker.py:214` / `authorize_comparison` | F | query/ORM | `fingerprints.get` | ver matriz |
| `backend/app/facial/search_worker.py:274` / `process_claimed_search_job` | F | produtor | `FacialSearchCandidate` | ver matriz |
| `backend/app/facial/search_worker.py:265` / `process_claimed_search_job` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search_worker.py:377` / `_request_is_authorized` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:500` / `_comparison_photo_is_current` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:588` / `_finish_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:595` / `_finish_request` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search_worker.py:255` / `process_claimed_search_job` | F | query/ORM | `current_fingerprints.get` | ver matriz |
| `backend/app/facial/search_worker.py:255` / `process_claimed_search_job` | F | query/ORM | `fingerprints.get` | ver matriz |
| `backend/app/facial/search_worker.py:257` / `process_claimed_search_job` | F | query/ORM | `fingerprints.get` | ver matriz |
| `backend/app/facial/search_worker.py:383` / `_request_is_authorized` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:367` / `_request_is_authorized` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:439` / `_refresh_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:506` / `_comparison_photo_is_current` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:532` / `_snapshot_items` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:419` / `_refresh_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:484` / `_comparison_photo_is_current` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:62` / `gallery_index_status` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/status.py:259` / `retry_all_failed_index_jobs` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/status.py:280` / `retry_all_failed_index_jobs` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/status.py:58` / `gallery_index_status` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/status.py:68` / `gallery_index_status` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/status.py:83` / `gallery_index_status` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/status.py:106` / `gallery_index_status` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/status.py:111` / `gallery_index_status` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/status.py:207` / `retry_failed_index_jobs` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/status.py:212` / `retry_failed_index_jobs` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/status.py:256` / `retry_all_failed_index_jobs` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/status.py:228` / `retry_failed_index_jobs` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/status.py:287` / `retry_all_failed_index_jobs` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/status.py:63` / `gallery_index_status` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:161` / `gallery_index_status` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/status.py:172` / `gallery_index_status` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/status.py:260` / `retry_all_failed_index_jobs` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:106` / `gallery_index_status` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:112` / `gallery_index_status` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:162` / `gallery_index_status` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:213` / `retry_failed_index_jobs` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:268` / `retry_all_failed_index_jobs` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:69` / `gallery_index_status` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:173` / `gallery_index_status` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/status.py:84` / `gallery_index_status` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/worker.py:55` / `process_claimed_index_job` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/worker.py:86` / `process_claimed_index_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/worker.py:87` / `process_claimed_index_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/worker.py:55` / `process_claimed_index_job` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/worker.py:95` / `process_claimed_index_job` | F | efeito potencial | `enqueue` | ver matriz |
| `backend/app/folder_access.py:47` / `_latest_reopening_expiry` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_access.py:203` / `folder_media_state` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_access.py:221` / `folder_media_state_by_id` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_access.py:235` / `historical_folder_media_state_by_id` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_access.py:249` / `folder_media_states_by_id` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_access.py:322` / `folder_media_access_by_id` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_access.py:358` / `photos_with_folder_media_access_by_id` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_access.py:393` / `folder_effective_expiries_by_id` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_access.py:428` / `gallery_media_writes_allowed` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_access.py:440` / `gallery_media_writes_allowed` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_access.py:25` / `_utc` | G | efeito potencial | `value.replace` | ver matriz |
| `backend/app/folder_access.py:409` / `folder_media_writes_allowed` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_access.py:462` / `lock_selected_content_folders` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_access.py:482` / `lock_selected_content_folders` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_access.py:35` / `_latest_reopening_expiry` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:221` / `folder_media_state_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:250` / `folder_media_states_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:323` / `folder_media_access_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:394` / `folder_effective_expiries_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:499` / `folder_browsing_clause` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:507` / `folder_browsing_clause` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:359` / `photos_with_folder_media_access_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:429` / `gallery_media_writes_allowed` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:278` / `_client_reopening_expiry_subquery` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:204` / `folder_media_state` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:235` / `historical_folder_media_state_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:410` / `folder_media_writes_allowed` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:521` / `folder_browsing_clause` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:441` / `gallery_media_writes_allowed` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:264` / `_latest_media_state_subquery` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:483` / `lock_selected_content_folders` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_access.py:463` / `lock_selected_content_folders` | G | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:32` / `folder_settings` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/folder_processing.py:37` / `folder_settings` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:45` / `initialize_folder_processing` | P | produtor | `FolderProcessingSettings` | ver matriz |
| `backend/app/folder_processing.py:53` / `initialize_folder_processing` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/folder_processing.py:84` / `facial_processing_allowed` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing.py:93` / `configure_folder` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing.py:96` / `configure_folder` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:109` / `configure_folder` | P | produtor | `FolderProcessingSettings` | ver matriz |
| `backend/app/folder_processing.py:110` / `configure_folder` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/folder_processing.py:118` / `configure_folder` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_processing.py:139` / `configure_folder` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing.py:33` / `folder_settings` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:140` / `configure_folder` | P | efeito potencial | `enqueue` | ver matriz |
| `backend/app/folder_processing.py:126` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:118` / `configure_folder` | P | query/ORM | `update` | ver matriz |
| `backend/app/folder_processing.py:96` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:120` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:46` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/folder_processing_api.py:38` / `folder_or_404` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing_api.py:41` / `folder_or_404` | P | query/ORM | `db.get` | ver matriz |
| `backend/app/folder_processing_api.py:61` / `configuration` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:53` / `configuration` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing_api.py:131` / `enqueue_folder_preview` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:157` / `reprocess_folder_facial` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:159` / `reprocess_folder_facial` | P | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/folder_processing_api.py:91` / `configuration` | P | query/ORM | `preview_counts.get` | ver matriz |
| `backend/app/folder_processing_api.py:132` / `enqueue_folder_preview` | P | efeito potencial | `enqueue_preview` | ver matriz |
| `backend/app/folder_processing_api.py:55` / `configuration` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_processing_api.py:53` / `configuration` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:127` / `enqueue_folder_preview` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:154` / `reprocess_folder_facial` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:61` / `configuration` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:55` / `configuration` | P | query/ORM | `select` | ver matriz |
| `backend/app/gallery_access.py:91` / `issue_gallery_capability` | G | gate | `owned_record` | ver matriz |
| `backend/app/gallery_access.py:106` / `issue_gallery_capability` | G | produtor | `GalleryAccessCapability` | ver matriz |
| `backend/app/gallery_access.py:121` / `issue_gallery_capability` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/gallery_access.py:200` / `rotate_gallery_capability` | G | gate | `owned_record` | ver matriz |
| `backend/app/gallery_access.py:97` / `issue_gallery_capability` | G | gate | `owned_record` | ver matriz |
| `backend/app/gallery_access.py:146` / `resolve_gallery_capability` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/gallery_access.py:165` / `resolve_gallery_capability` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_access.py:94` / `issue_gallery_capability` | G | gate | `owned_record` | ver matriz |
| `backend/app/gallery_access.py:100` / `issue_gallery_capability` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_access.py:160` / `resolve_gallery_capability` | G | query/ORM | `select` | ver matriz |
| `backend/app/gallery_access.py:100` / `issue_gallery_capability` | G | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:77` / `_delete_count` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/gallery_cleanup.py:95` / `remove_operational_storage` | L | query/ORM | `manifest.get` | ver matriz |
| `backend/app/gallery_cleanup.py:118` / `remove_operational_storage` | L | query/ORM | `storage_manifest.get` | ver matriz |
| `backend/app/gallery_cleanup.py:119` / `remove_operational_storage` | L | query/ORM | `storage_manifest.get` | ver matriz |
| `backend/app/gallery_cleanup.py:130` / `remove_operational_storage` | L | query/ORM | `_db.scalars` | ver matriz |
| `backend/app/gallery_cleanup.py:197` / `remove_operational_records` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/gallery_cleanup.py:202` / `remove_operational_records` | L | gate | `owned_record` | ver matriz |
| `backend/app/gallery_cleanup.py:205` / `remove_operational_records` | L | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/gallery_cleanup.py:213` / `remove_operational_records` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/gallery_cleanup.py:222` / `_remove_client_link_records` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_cleanup.py:292` / `_remove_client_link_records` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/gallery_cleanup.py:38` / `prepare_lifecycle_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_cleanup.py:101` / `remove_operational_storage` | L | query/ORM | `storage_manifest.get` | ver matriz |
| `backend/app/gallery_cleanup.py:186` / `remove_operational_records` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/gallery_cleanup.py:187` / `remove_operational_records` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/gallery_cleanup.py:213` / `remove_operational_records` | L | produtor | `AuditEvent` | ver matriz |
| `backend/app/gallery_cleanup.py:293` / `_remove_client_link_records` | L | produtor | `AuditEvent` | ver matriz |
| `backend/app/gallery_cleanup.py:46` / `prepare_lifecycle_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_cleanup.py:149` / `remove_operational_storage` | L | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/gallery_cleanup.py:229` / `_remove_client_link_records` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/gallery_cleanup.py:130` / `remove_operational_storage` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:135` / `remove_operational_storage` | L | query/ORM | `storage_manifest.get` | ver matriz |
| `backend/app/gallery_cleanup.py:143` / `remove_operational_storage` | L | gate | `media_namespace` | ver matriz |
| `backend/app/gallery_cleanup.py:197` / `remove_operational_records` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:223` / `_remove_client_link_records` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:39` / `prepare_lifecycle_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:186` / `remove_operational_records` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:47` / `prepare_lifecycle_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:77` / `_delete_count` | L | query/ORM | `delete` | ver matriz |
| `backend/app/gallery_cleanup.py:230` / `_remove_client_link_records` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cleanup.py:105` / `remove_operational_storage` | L | query/ORM | `entry.get` | ver matriz |
| `backend/app/gallery_cleanup.py:187` / `remove_operational_records` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cover_readiness.py:22` / `gallery_cover_readiness` | G | gate | `owned_record` | ver matriz |
| `backend/app/gallery_cover_readiness.py:25` / `gallery_cover_readiness` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_cover_readiness.py:40` / `gallery_cover_readiness` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_cover_readiness.py:17` / `gallery_cover_readiness` | G | gate | `owned_record` | ver matriz |
| `backend/app/gallery_cover_readiness.py:25` / `gallery_cover_readiness` | G | query/ORM | `select` | ver matriz |
| `backend/app/gallery_cover_readiness.py:40` / `gallery_cover_readiness` | G | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:79` / `transition_operation` | L | query/ORM | `OPERATION_TRANSITIONS.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:301` / `gallery_operational_storage_manifest` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/gallery_lifecycle.py:316` / `claim_next_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_lifecycle.py:354` / `require_lifecycle_origin` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/gallery_lifecycle.py:361` / `require_lifecycle_origin` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_lifecycle.py:100` / `gallery_deletion_inventory` | L | gate | `owned_record` | ver matriz |
| `backend/app/gallery_lifecycle.py:118` / `gallery_deletion_inventory` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_lifecycle.py:157` / `client_unlink_inventory` | L | gate | `owned_record` | ver matriz |
| `backend/app/gallery_lifecycle.py:159` / `client_unlink_inventory` | L | gate | `owned_record` | ver matriz |
| `backend/app/gallery_lifecycle.py:267` / `gallery_operational_storage_manifest` | L | gate | `owned_record` | ver matriz |
| `backend/app/gallery_lifecycle.py:357` / `require_lifecycle_origin` | L | gate | `owned_record` | ver matriz |
| `backend/app/gallery_lifecycle.py:403` / `process_claimed_operation` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:108` / `count` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_lifecycle.py:112` / `gallery_deletion_inventory` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/gallery_lifecycle.py:174` / `count` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/gallery_lifecycle.py:182` / `client_unlink_inventory` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/gallery_lifecycle.py:272` / `gallery_operational_storage_manifest` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/gallery_lifecycle.py:280` / `gallery_operational_storage_manifest` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/gallery_lifecycle.py:355` / `require_lifecycle_origin` | L | gate | `require_admin_tenant` | ver matriz |
| `backend/app/gallery_lifecycle.py:359` / `require_lifecycle_origin` | L | gate | `owned_record` | ver matriz |
| `backend/app/gallery_lifecycle.py:375` / `retry_failed_operation` | L | query/ORM | `(operation.manifest or {}).get` | ver matriz |
| `backend/app/gallery_lifecycle.py:416` / `process_claimed_operation` | L | query/ORM | `manifest.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:422` / `process_claimed_operation` | L | query/ORM | `handlers.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:451` / `process_claimed_operation` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:460` / `process_claimed_operation` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:102` / `gallery_deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:105` / `gallery_deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:119` / `gallery_deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:161` / `client_unlink_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:165` / `client_unlink_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:176` / `client_unlink_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:251` / `client_unlink_inventory` | L | query/ORM | `order_counts.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:253` / `client_unlink_inventory` | L | query/ORM | `order_counts.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:269` / `gallery_operational_storage_manifest` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:432` / `process_claimed_operation` | L | query/ORM | `manifest.get` | ver matriz |
| `backend/app/gallery_lifecycle.py:301` / `gallery_operational_storage_manifest` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:361` / `require_lifecycle_origin` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:302` / `gallery_operational_storage_manifest` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:142` / `gallery_deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:108` / `count` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:113` / `gallery_deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:174` / `count` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:183` / `client_unlink_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:273` / `gallery_operational_storage_manifest` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:281` / `gallery_operational_storage_manifest` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:302` / `gallery_operational_storage_manifest` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:123` / `gallery_deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:120` / `gallery_deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:317` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:321` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_lifecycle.py:326` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/gallery_pricing.py:30` / `quote_parent_gallery` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/gallery_pricing.py:63` / `quote_loaded_gallery` | K | query/ORM | `configured.get` | ver matriz |
| `backend/app/gallery_pricing.py:64` / `quote_loaded_gallery` | K | query/ORM | `configured.get` | ver matriz |
| `backend/app/gallery_pricing.py:65` / `quote_loaded_gallery` | K | query/ORM | `configured.get` | ver matriz |
| `backend/app/gallery_pricing.py:66` / `quote_loaded_gallery` | K | query/ORM | `configured.get` | ver matriz |
| `backend/app/gallery_pricing.py:32` / `quote_parent_gallery` | K | query/ORM | `db.scalars` | ver matriz |
| `backend/app/gallery_pricing.py:32` / `quote_parent_gallery` | K | query/ORM | `select` | ver matriz |
| `backend/app/gallery_visuals.py:69` / `normalize_title_font` | G | query/ORM | `LEGACY_TITLE_FONT_TOKENS.get` | ver matriz |
| `backend/app/global_pix.py:73` / `global_pix_settings` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/global_pix.py:74` / `global_pix_settings` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/global_pix.py:31` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:55` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:56` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:101` / `pix_payload` | K | query/ORM | `result.update` | ver matriz |
| `backend/app/global_pix.py:128` / `apply_configuration` | K | produtor | `GlobalPixSettings` | ver matriz |
| `backend/app/global_pix.py:129` / `apply_configuration` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/global_pix.py:143` / `proposal_preview` | K | produtor | `GlobalPixSettings` | ver matriz |
| `backend/app/global_pix.py:32` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:33` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:46` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:48` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:117` / `apply_configuration` | K | gate | `require_admin_tenant` | ver matriz |
| `backend/app/global_pix.py:124` / `apply_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:124` / `apply_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:57` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:74` / `global_pix_settings` | K | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_client.py:30` / `_request` | O | produtor | `httpx.Client` | ver matriz |
| `backend/app/google_drive_client.py:48` / `stream_get` | O | produtor | `httpx.Client` | ver matriz |
| `backend/app/google_drive_oauth.py:102` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/google_drive_oauth.py:237` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/google_drive_oauth.py:104` / `status` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/google_drive_oauth.py:130` / `observe_storage_quota` | A | query/ORM | `token_data.get` | ver matriz |
| `backend/app/google_drive_oauth.py:133` / `observe_storage_quota` | A | query/ORM | `adapter.get` | ver matriz |
| `backend/app/google_drive_oauth.py:141` / `observe_storage_quota` | A | query/ORM | `about_data.get` | ver matriz |
| `backend/app/google_drive_oauth.py:146` / `observe_storage_quota` | A | query/ORM | `quota.get` | ver matriz |
| `backend/app/google_drive_oauth.py:147` / `observe_storage_quota` | A | query/ORM | `quota.get` | ver matriz |
| `backend/app/google_drive_oauth.py:98` / `_expired` | A | efeito potencial | `expires_at.replace` | ver matriz |
| `backend/app/google_drive_oauth.py:108` / `status` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:198` / `connect` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:225` / `connect` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/google_drive_oauth.py:245` / `callback` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:251` / `callback` | A | efeito potencial | `_cipher().decrypt` | ver matriz |
| `backend/app/google_drive_oauth.py:267` / `callback` | A | query/ORM | `token_data.get` | ver matriz |
| `backend/app/google_drive_oauth.py:268` / `callback` | A | query/ORM | `token_data.get` | ver matriz |
| `backend/app/google_drive_oauth.py:275` / `callback` | A | efeito potencial | `_cipher().encrypt(refresh, tenant_id=tenant_id, credential_id=connection_id).payload` | ver matriz |
| `backend/app/google_drive_oauth.py:280` / `callback` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:303` / `revoke` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:313` / `revoke` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:80` / `_owner` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/google_drive_oauth.py:167` / `observe_quota` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:172` / `observe_quota` | A | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/google_drive_oauth.py:178` / `observe_quota` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/google_drive_oauth.py:206` / `connect` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:221` / `connect` | A | efeito potencial | `cipher.encrypt(verifier, tenant_id=tenant_id, credential_id=attempt_id).payload` | ver matriz |
| `backend/app/google_drive_oauth.py:225` / `connect` | A | produtor | `GoogleDriveOAuthAttempt` | ver matriz |
| `backend/app/google_drive_oauth.py:285` / `callback` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/google_drive_oauth.py:310` / `revoke` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/google_drive_oauth.py:325` / `revoke` | A | efeito potencial | `_cipher().decrypt` | ver matriz |
| `backend/app/google_drive_oauth.py:275` / `callback` | A | efeito potencial | `_cipher().encrypt` | ver matriz |
| `backend/app/google_drive_oauth.py:285` / `callback` | A | produtor | `GoogleDriveConnection` | ver matriz |
| `backend/app/google_drive_oauth.py:108` / `status` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:198` / `connect` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:221` / `connect` | A | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/google_drive_oauth.py:245` / `callback` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:280` / `callback` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:303` / `revoke` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:313` / `revoke` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:167` / `observe_quota` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:206` / `connect` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_oauth.py:310` / `revoke` | A | query/ORM | `select` | ver matriz |
| `backend/app/google_drive_storage.py:119` / `_metadata` | O | query/ORM | `resource.get` | ver matriz |
| `backend/app/google_drive_storage.py:120` / `_metadata` | O | query/ORM | `resource.get` | ver matriz |
| `backend/app/google_drive_storage.py:121` / `_metadata` | O | query/ORM | `resource.get` | ver matriz |
| `backend/app/google_drive_storage.py:122` / `_metadata` | O | query/ORM | `resource.get` | ver matriz |
| `backend/app/google_drive_storage.py:203` / `upload_drive_file` | O | query/ORM | `started.headers.get` | ver matriz |
| `backend/app/google_drive_storage.py:217` / `upload_drive_file` | O | query/ORM | `md5_digest.update` | ver matriz |
| `backend/app/google_drive_storage.py:218` / `upload_drive_file` | O | query/ORM | `sha256_digest.update` | ver matriz |
| `backend/app/google_drive_storage.py:48` / `provider_failure_code` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/google_drive_storage.py:49` / `provider_failure_code` | O | query/ORM | `error.get` | ver matriz |
| `backend/app/google_drive_storage.py:128` / `_metadata` | O | query/ORM | `resource.get` | ver matriz |
| `backend/app/google_drive_storage.py:129` / `_metadata` | O | query/ORM | `resource.get` | ver matriz |
| `backend/app/google_drive_storage.py:51` / `provider_failure_code` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/google_drive_storage.py:253` / `upload_drive_file` | O | query/ORM | `result.headers.get` | ver matriz |
| `backend/app/google_drive_storage.py:52` / `provider_failure_code` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/historical_media.py:47` / `historical_media_path` | X | gate | `media_namespace` | ver matriz |
| `backend/app/historical_media.py:57` / `historical_media_path` | X | gate | `media_namespace` | ver matriz |
| `backend/app/historical_media.py:65` / `_checksum` | X | efeito potencial | `path.open` | ver matriz |
| `backend/app/historical_media.py:91` / `_copy_deterministic` | X | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/historical_media.py:93` / `_copy_deterministic` | X | efeito potencial | `temporary.unlink` | ver matriz |
| `backend/app/historical_media.py:126` / `prepare_confirmed_historical_media` | X | gate | `owned_record` | ver matriz |
| `backend/app/historical_media.py:139` / `prepare_confirmed_historical_media` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/historical_media.py:154` / `prepare_confirmed_historical_media` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/historical_media.py:155` / `prepare_confirmed_historical_media` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/historical_media.py:179` / `prepare_confirmed_historical_media` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/historical_media.py:232` / `prepare_confirmed_historical_media` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/historical_media.py:67` / `_checksum` | X | query/ORM | `digest.update` | ver matriz |
| `backend/app/historical_media.py:86` / `_copy_deterministic` | X | efeito potencial | `source.open` | ver matriz |
| `backend/app/historical_media.py:86` / `_copy_deterministic` | X | efeito potencial | `temporary.open` | ver matriz |
| `backend/app/historical_media.py:87` / `_copy_deterministic` | X | efeito potencial | `copyfileobj` | ver matriz |
| `backend/app/historical_media.py:128` / `prepare_confirmed_historical_media` | X | query/ORM | `select` | ver matriz |
| `backend/app/historical_media.py:142` / `prepare_confirmed_historical_media` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/historical_media.py:165` / `prepare_confirmed_historical_media` | X | produtor | `CommercialHistoryMedia` | ver matriz |
| `backend/app/historical_media.py:170` / `prepare_confirmed_historical_media` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/historical_media.py:176` / `prepare_confirmed_historical_media` | X | gate | `owned_record` | ver matriz |
| `backend/app/historical_media.py:180` / `prepare_confirmed_historical_media` | X | query/ORM | `select` | ver matriz |
| `backend/app/historical_media.py:193` / `authorize_copy` | X | gate | `owned_record` | ver matriz |
| `backend/app/historical_media.py:194` / `authorize_copy` | X | gate | `owned_record` | ver matriz |
| `backend/app/historical_media.py:156` / `prepare_confirmed_historical_media` | X | query/ORM | `select` | ver matriz |
| `backend/app/historical_media.py:143` / `prepare_confirmed_historical_media` | X | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:289` / `execute` | L | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `backend/app/homolog_cleanup.py:290` / `execute` | L | query/ORM | `schema_map.get` | ver matriz |
| `backend/app/homolog_cleanup.py:294` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:295` / `execute` | L | gate | `require_single_tenant` | ver matriz |
| `backend/app/homolog_cleanup.py:302` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:316` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:334` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:335` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:336` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:339` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:344` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:349` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:350` / `execute` | L | gate | `require_single_tenant` | ver matriz |
| `backend/app/homolog_cleanup.py:294` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:302` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:316` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:324` / `execute` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:326` / `execute` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:343` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:349` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:143` / `_count` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:146` / `_count` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:254` / `_clear_media_root` | L | efeito potencial | `entry.unlink` | ver matriz |
| `backend/app/homolog_cleanup.py:263` / `has_mercadopago_financial_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:265` / `has_mercadopago_financial_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:266` / `has_mercadopago_financial_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:267` / `has_mercadopago_financial_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:272` / `has_credit_wallet_history` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:343` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:370` / `operational_delete_order` | L | query/ORM | `targets.add` | ver matriz |
| `backend/app/homolog_cleanup.py:303` / `execute` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:334` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:335` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:336` / `execute` | L | query/ORM | `update` | ver matriz |
| `backend/app/homolog_cleanup.py:344` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:265` / `has_mercadopago_financial_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:266` / `has_mercadopago_financial_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:267` / `has_mercadopago_financial_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:272` / `has_credit_wallet_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:339` / `execute` | L | query/ORM | `update` | ver matriz |
| `backend/app/homolog_cleanup.py:324` / `execute` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:326` / `execute` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:263` / `has_mercadopago_financial_history` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:303` / `execute` | L | query/ORM | `select` | ver matriz |
| `backend/app/installation_operator.py:14` / `operator_is_active` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/installation_operator.py:21` / `require_operator` | O | gate | `operator_is_active` | ver matriz |
| `backend/app/installation_operator.py:14` / `operator_is_active` | O | query/ORM | `select` | ver matriz |
| `backend/app/integration_secrets.py:146` / `encrypt` | X | efeito potencial | `AESGCM(self._keys[self.active_key_id]).encrypt` | ver matriz |
| `backend/app/integration_secrets.py:161` / `rotate` | X | efeito potencial | `self.encrypt` | ver matriz |
| `backend/app/integration_secrets.py:62` / `__init__` | X | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/integration_secrets.py:154` / `decrypt` | X | efeito potencial | `AESGCM(self._keys[envelope.key_id]).decrypt(envelope.nonce, envelope.ciphertext, self._aad(tenant_id, credential_id, envelope)).decode` | ver matriz |
| `backend/app/integration_secrets.py:161` / `rotate` | X | efeito potencial | `self.decrypt` | ver matriz |
| `backend/app/integration_secrets.py:61` / `__init__` | X | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/integration_secrets.py:154` / `decrypt` | X | efeito potencial | `AESGCM(self._keys[envelope.key_id]).decrypt` | ver matriz |
| `backend/app/main.py:1311` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:1353` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:1464` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2487` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2502` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2564` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2570` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2595` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2622` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2874` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2886` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2966` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3031` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3426` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3437` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3445` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3455` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3468` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3504` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3515` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3526` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3543` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3572` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3582` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3639` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3647` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3663` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3680` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3690` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3700` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3779` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3790` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3803` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3831` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3894` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3906` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4031` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4050` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4376` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4485` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4543` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4651` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4673` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4725` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4838` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4977` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4989` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5062` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5228` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5251` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5325` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5337` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5514` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5702` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5869` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5913` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5976` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:6103` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:6510` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6600` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:6713` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:6808` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6840` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6889` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:6949` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7134` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7485` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7582` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7899` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7995` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8017` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8542` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8563` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8587` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8617` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8649` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8814` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8894` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:8927` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9141` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9170` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9206` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9318` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9396` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:9430` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:9495` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9763` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:9782` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9856` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9942` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10010` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10045` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10130` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10359` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10426` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10508` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10567` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10722` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10887` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11219` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11276` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:11306` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:11334` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11582` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11623` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11640` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11670` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11700` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11754` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11802` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11929` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12046` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12250` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:12380` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12431` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12470` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12604` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12624` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12646` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:12675` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:12755` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12893` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12923` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:13027` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:13109` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:13137` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:13165` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:13240` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:13401` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:13470` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:13870` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:13918` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:13946` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:13988` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:14003` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:14013` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:14040` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:14086` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:14118` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:14847` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:14867` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:15044` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:15100` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:15124` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:15147` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:15172` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:608` / `read_bounded_body` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1114` / `directory_tenant_id` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1121` / `require_same_origin` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1154` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1155` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1164` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1183` / `require_parent_gallery_mutable` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1197` / `require_derived_gallery_mutable` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1214` / `assigned_photo_for_gallery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:1215` / `assigned_photo_for_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1231` / `assigned_photo_for_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1301` / `_client_journey_destination` | X | query/ORM | `private_by_parent.get` | ver matriz |
| `backend/app/main.py:1318` / `whatsapp_webhook` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1319` / `whatsapp_webhook` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1355` / `admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1377` / `provision_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1378` / `provision_admin_whatsapp_channel` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1423` / `update_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1433` / `refresh_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1445` / `pair_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1470` / `admin_whatsapp_deliveries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1498` / `retry_admin_whatsapp_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1499` / `retry_admin_whatsapp_delivery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1561` / `validate_client_capability_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1614` / `client_challenge_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1648` / `_purchase_return_destination` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1668` / `_active_client_reauthentication_parent` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1806` / `client_resend` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1812` / `client_resend` | X | efeito potencial | `resend_client_challenge` | ver matriz |
| `backend/app/main.py:1827` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2107` / `admin_password` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2124` / `admin_password` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2130` / `admin_password` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2148` / `admin_totp` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2247` / `issue_admin_totp_recovery_codes` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:2253` / `issue_admin_totp_recovery_codes` | X | query/ORM | `db.add_all` | ver matriz |
| `backend/app/main.py:2285` / `admin_recovery_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2367` / `admin_recovery_reset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2376` / `admin_recovery_reset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2445` / `confirm_admin_email` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2458` / `confirm_admin_email` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2512` / `authenticated_identity` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2520` / `authenticated_identity` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2573` / `admin_email_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2646` / `admin_global_pix_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2684` / `admin_global_pix_confirm` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2685` / `admin_global_pix_confirm` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2879` / `public_branding` | X | gate | `branding_tenant_id` | ver matriz |
| `backend/app/main.py:2882` / `public_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2890` / `admin_branding` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2891` / `admin_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2900` / `update_admin_branding` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2901` / `update_admin_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2915` / `update_visual_protection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2916` / `update_visual_protection` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2942` / `upload_branding_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2951` / `upload_branding_asset` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:2952` / `upload_branding_asset` | X | efeito potencial | `temporary.write_bytes` | ver matriz |
| `backend/app/main.py:2953` / `upload_branding_asset` | X | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/main.py:2954` / `upload_branding_asset` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2973` / `public_branding_asset` | X | gate | `branding_tenant_id` | ver matriz |
| `backend/app/main.py:2976` / `public_branding_asset` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2998` / `public_branding_asset` | X | query/ORM | `{'.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon'}.get` | ver matriz |
| `backend/app/main.py:3036` / `admin_validation_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3234` / `_credit_owner_mutation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3240` / `_credit_owner_mutation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3315` / `_credit_owner_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3341` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3346` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3410` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3439` / `admin_credit_wallet` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3450` / `admin_media_archive_recovery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3463` / `admin_media_archive_recovery_candidates` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3474` / `admin_media_archive_recoveries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3490` / `admin_request_media_archive_recovery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3510` / `admin_credit_history` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3521` / `admin_credit_folder_history` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3534` / `admin_active_credit_packages` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3548` / `admin_photo_credit_operation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3551` / `admin_photo_credit_operation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3555` / `admin_photo_credit_operation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3577` / `admin_credit_entries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3724` / `admin_review_credit_purchase` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:3796` / `admin_capacity_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:3811` / `admin_facial_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:3824` / `admin_facial_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:3839` / `admin_clients` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3850` / `create_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3856` / `create_client` | X | produtor | `Client` | ver matriz |
| `backend/app/main.py:3857` / `create_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3859` / `create_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3884` / `update_client_name` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3885` / `update_client_name` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3898` / `get_client_deletion_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3900` / `get_client_deletion_inventory` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3910` / `delete_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4035` / `admin_parent_galleries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4037` / `admin_parent_galleries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4060` / `parent_gallery_overview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4064` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4113` / `_parent_gallery_or_404` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4149` / `_active_gallery_capability` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4160` / `_gallery_cover_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4180` / `_cover_preview_url` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4194` / `_archive_object_state` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4248` / `_local_cover_thumbnail_parent_ids` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4288` / `_admin_photo_preview_available` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4296` / `_admin_photo_preview_available` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4316` / `_cover_derivative` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4324` / `_client_preview_derivative` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4348` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4349` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4358` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4364` / `_cover_assets_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:4371` / `_cover_assets_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4381` / `parent_gallery_editor` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4489` / `parent_gallery_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4518` / `update_parent_gallery_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4547` / `parent_gallery_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4577` / `parent_gallery_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4608` / `set_parent_gallery_cover` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4611` / `set_parent_gallery_cover` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4618` / `set_parent_gallery_cover` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4621` / `set_parent_gallery_cover` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4657` / `clear_parent_gallery_cover` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4660` / `clear_parent_gallery_cover` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4677` / `parent_gallery_sales` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4704` / `update_parent_gallery_sales` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4729` / `parent_gallery_details` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4791` / `register_parent_gallery_cover_photo` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4796` / `register_parent_gallery_cover_photo` | X | efeito potencial | `require_upload_ready` | ver matriz |
| `backend/app/main.py:4798` / `register_parent_gallery_cover_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4811` / `register_parent_gallery_cover_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4844` / `admin_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4863` / `prepare_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4894` / `activate_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4933` / `suspend_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4958` / `revoke_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4983` / `admin_parent_gallery_facial_cleanup_proof` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4997` / `admin_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5066` / `admin_private_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5140` / `retry_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5179` / `reprocess_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5232` / `admin_parent_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5236` / `admin_parent_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5258` / `admin_parent_gallery_available_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5329` / `admin_parent_gallery_private_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5346` / `admin_parent_gallery_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5454` / `create_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5462` / `create_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5469` / `create_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5477` / `create_photo_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:5486` / `create_photo_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5504` / `_admin_linked_gallery_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5519` / `admin_client_restricted_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5578` / `create_admin_client_restricted_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5589` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5592` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5605` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5610` / `create_admin_client_restricted_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:5617` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5619` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5645` / `grant_restricted_folder_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5647` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5660` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5710` / `revoke_restricted_folder_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5712` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5713` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5722` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5733` / `revoke_restricted_folder_client` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5740` / `revoke_restricted_folder_client` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:5753` / `rename_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5755` / `rename_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5782` / `renew_public_photo_folder_deadline` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5784` / `renew_public_photo_folder_deadline` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5793` / `renew_public_photo_folder_deadline` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5797` / `renew_public_photo_folder_deadline` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5833` / `configure_photo_folder_deadline` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5835` / `configure_photo_folder_deadline` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5873` / `delete_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5875` / `delete_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5878` / `delete_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5902` / `delete_photo_folder` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5906` / `delete_photo_folder` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:5907` / `delete_photo_folder` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:5918` / `admin_photo_folder_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5929` / `admin_photo_folder_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5984` / `delete_folder_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5986` / `delete_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5991` / `delete_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6012` / `delete_folder_photo_asset` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:6023` / `_assert_photo_credit_operations_settled` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6042` / `_delete_photo_records` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:6062` / `_delete_photo_records` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6065` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6066` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6067` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6068` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6069` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6072` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6073` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6074` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6075` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6077` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6089` / `_delete_photo_records` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:6112` / `delete_folder_photo_assets` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6114` / `delete_folder_photo_assets` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6145` / `register_folder_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6150` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6178` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6187` / `register_folder_photo_asset` | X | efeito potencial | `require_upload_ready` | ver matriz |
| `backend/app/main.py:6245` / `register_folder_photo_asset` | X | produtor | `PhotoAsset` | ver matriz |
| `backend/app/main.py:6254` / `register_folder_photo_asset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6276` / `_publish_photo_folder` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:6280` / `_publish_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6375` / `publish_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6378` / `publish_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6388` / `publish_photo_folder` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:6399` / `publish_parent_gallery_ready_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6435` / `release_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6446` / `release_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6456` / `release_photo_folder` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:6463` / `create_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6467` / `create_parent_gallery` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:6469` / `create_parent_gallery` | X | produtor | `ParentGallery` | ver matriz |
| `backend/app/main.py:6470` / `create_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6514` / `parent_gallery_public_link_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6546` / `issue_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6576` / `rotate_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6607` / `revoke_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6662` / `issue_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6665` / `issue_parent_gallery_client_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6689` / `rotate_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6723` / `revoke_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6742` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:6815` / `parent_gallery_deletion_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6850` / `parent_gallery_client_unlink_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6853` / `parent_gallery_client_unlink_inventory` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6854` / `parent_gallery_client_unlink_inventory` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6898` / `delete_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6906` / `delete_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6923` / `delete_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6930` / `delete_parent_gallery` | X | produtor | `GalleryLifecycleOperation` | ver matriz |
| `backend/app/main.py:6942` / `delete_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6953` / `gallery_lifecycle_operation_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6955` / `gallery_lifecycle_operation_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6967` / `retry_gallery_lifecycle_operation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6969` / `retry_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6996` / `cancel_gallery_lifecycle_operation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6998` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7068` / `clone_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7086` / `challenge_client_phone` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7087` / `challenge_client_phone` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7098` / `challenge_client_phone` | X | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/main.py:7106` / `change_client_phone` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7107` / `change_client_phone` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7111` / `change_client_phone` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:7138` / `parent_gallery_clients` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7332` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7425` / `link_admin_client_to_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7455` / `update_admin_client_gallery_access` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7458` / `update_admin_client_gallery_access` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7464` / `update_admin_client_gallery_access` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7498` / `unlink_admin_client_from_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7506` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7523` / `unlink_admin_client_from_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7524` / `unlink_admin_client_from_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7527` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7537` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7555` / `unlink_admin_client_from_parent_gallery` | X | produtor | `GalleryLifecycleOperation` | ver matriz |
| `backend/app/main.py:7575` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:7589` / `selection_detail` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7591` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7604` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7658` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7808` / `_purchase_photo_interaction_html` | X | query/ORM | `interaction.get` | ver matriz |
| `backend/app/main.py:7813` / `_purchase_photo_interaction_html` | X | query/ORM | `interaction.get` | ver matriz |
| `backend/app/main.py:7826` / `_selection_html_preview` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:7855` / `_selection_html_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7872` / `_selection_html_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7907` / `export_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7911` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7975` / `export_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7998` / `export_finalized_order` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8000` / `export_finalized_order` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8003` / `export_finalized_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8026` / `export_canonical_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8030` / `export_canonical_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8031` / `export_canonical_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8032` / `export_canonical_selection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8137` / `register_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8188` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8193` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8197` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8203` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8211` / `import_photo_source` | X | efeito potencial | `require_upload_ready` | ver matriz |
| `backend/app/main.py:8230` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8536` / `import_photo_source` | X | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/main.py:8547` / `photo_media_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8549` / `photo_media_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8552` / `photo_media_status` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8557` / `photo_media_status` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8567` / `admin_photo_facial_analysis` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8593` / `admin_photo_preview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8594` / `admin_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8599` / `admin_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8623` / `admin_watermarked_photo_preview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8624` / `admin_watermarked_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8629` / `admin_watermarked_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8657` / `admin_purchase_history` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8760` / `_pricing_preset_payload` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:8793` / `_replace_pricing_preset_tiers` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:8794` / `_replace_pricing_preset_tiers` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8800` / `_replace_pricing_preset_tiers` | X | query/ORM | `db.add_all` | ver matriz |
| `backend/app/main.py:8820` / `list_progressive_pricing_presets` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8836` / `create_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8838` / `create_progressive_pricing_preset` | X | produtor | `ProgressivePricingPreset` | ver matriz |
| `backend/app/main.py:8861` / `_pricing_preset_or_404` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8874` / `update_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8900` / `deactivate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8916` / `activate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8934` / `simulate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9125` / `save_parent_pricing` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:9126` / `save_parent_pricing` | X | query/ORM | `db.add_all` | ver matriz |
| `backend/app/main.py:9145` / `admin_parent_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9158` / `save_admin_parent_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9174` / `admin_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9176` / `admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9179` / `admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9196` / `save_admin_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9212` / `admin_gallery_orders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9214` / `admin_gallery_orders` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9280` / `create_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9282` / `create_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9283` / `create_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9324` / `private_gallery_link_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9340` / `private_gallery_link_status` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9369` / `issue_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9386` / `rotate_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9403` / `revoke_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9405` / `revoke_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9424` / `rotate_private_gallery_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9439` / `revoke_private_gallery_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9506` / `private_gallery_members` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9508` / `private_gallery_members` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9514` / `private_gallery_members` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9568` / `add_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9571` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9572` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9662` / `_change_private_member_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9699` / `_change_private_member_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9700` / `_change_private_member_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9732` / `block_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9751` / `unblock_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9770` / `unlink_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9798` / `admin_gallery_membership_notifications` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9848` / `read_admin_gallery_membership_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9862` / `list_admin_media_archive_notices` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9922` / `read_admin_media_archive_notice` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9923` / `read_admin_media_archive_notice` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9945` / `list_private_upload_batches` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9948` / `list_private_upload_batches` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9958` / `begin_private_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9962` / `begin_private_upload_batch` | X | efeito potencial | `require_upload_ready` | ver matriz |
| `backend/app/main.py:9975` / `finish_private_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9991` / `begin_restricted_folder_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:9995` / `begin_restricted_folder_upload_batch` | X | efeito potencial | `require_upload_ready` | ver matriz |
| `backend/app/main.py:9996` / `begin_restricted_folder_upload_batch` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10013` / `list_restricted_folder_upload_batches` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10015` / `list_restricted_folder_upload_batches` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10022` / `list_restricted_folder_upload_batches` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10033` / `finish_restricted_folder_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10049` / `admin_private_gallery_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10098` / `create_private_gallery_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10103` / `create_private_gallery_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10109` / `create_private_gallery_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:10118` / `create_private_gallery_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10134` / `admin_private_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10136` / `admin_private_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10346` / `add_admin_private_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10366` / `remove_admin_private_gallery_photo` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10369` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10396` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10430` / `delete_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10432` / `delete_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10436` / `delete_derived_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10440` / `delete_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10461` / `delete_derived_gallery` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:10521` / `list_derived_galleries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10571` / `derived_gallery_detail` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10573` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10577` / `derived_gallery_detail` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10583` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10584` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10649` / `update_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10666` / `renew_gallery_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10678` / `_reopening_request_payload` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10730` / `list_gallery_reopening_requests` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10789` / `decide_gallery_reopening_request` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10791` / `decide_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10868` / `retry_gallery_reopening_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10869` / `retry_gallery_reopening_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10933` / `client_library` | X | query/ORM | `parent_ids.update` | ver matriz |
| `backend/app/main.py:11045` / `client_library` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11213` / `_commerce_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11281` / `remove_unified_cart_group` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11311` / `remove_unified_cart_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11556` / `_historical_item_for_client` | X | gate | `client_tenant_id` | ver matriz |
| `backend/app/main.py:11557` / `_historical_item_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11570` / `_historical_item_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11589` / `client_purchased_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11603` / `client_purchased_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11604` / `client_purchased_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11765` / `gallery_released_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11841` / `gallery_review` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11940` / `client_gallery_cover_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11995` / `_client_photo_preview_is_available` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12011` / `_client_photo_preview_is_available` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12082` / `client_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12095` / `client_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12126` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12267` / `unselect_photo_from_public_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12403` / `public_gallery_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12553` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:12563` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:12964` / `public_gallery_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13010` / `favorite_canonical_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13040` / `unfavorite_canonical_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13062` / `record_canonical_photo_view` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13095` / `create_canonical_photo_comment` | X | produtor | `PhotoComment` | ver matriz |
| `backend/app/main.py:13102` / `create_canonical_photo_comment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13125` / `canonical_client_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:13147` / `remove_canonical_comment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13232` / `_canonical_cart_payload` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:13274` / `_client_folder_for_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13284` / `_latest_folder_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13337` / `_create_folder_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13380` / `_create_folder_reopening_request` | X | produtor | `GalleryReopeningRequest` | ver matriz |
| `backend/app/main.py:13388` / `_create_folder_reopening_request` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13390` / `_create_folder_reopening_request` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:13391` / `_create_folder_reopening_request` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13484` / `canonical_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13514` / `request_canonical_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13546` / `checkout_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:13578` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13587` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13604` / `communicate_payment` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:13614` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13628` / `communicate_payment` | X | produtor | `PaymentCommunication` | ver matriz |
| `backend/app/main.py:13634` / `communicate_payment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13637` / `communicate_payment` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:13672` / `decide_payment_communication` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:13681` / `decide_payment_communication` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:13694` / `decide_payment_communication` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:13721` / `correct_payment_confirmation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:13728` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13740` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13747` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13764` / `correct_payment_confirmation` | X | query/ORM | `{'confirmed': 'confirmed', 'refused': 'cancelled'}.get` | ver matriz |
| `backend/app/main.py:13777` / `correct_payment_confirmation` | X | produtor | `PaymentConfirmationCorrection` | ver matriz |
| `backend/app/main.py:13786` / `correct_payment_confirmation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13835` / `update_order_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:13851` / `resend_order_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:13876` / `push_subscription_state` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13925` / `unregister_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:13928` / `unregister_push_subscription` | X | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/main.py:13950` / `list_notification_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:13992` / `list_payment_templates` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:14024` / `admin_removed_photo_movements` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:14047` / `admin_order_item_preview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:14048` / `admin_order_item_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:14051` / `admin_order_item_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:14057` / `admin_order_item_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:14069` / `admin_order_item_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:14099` / `export_payment_orders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:14134` / `list_payment_communications` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:14709` / `_payment_financial_priority` | X | query/ORM | `{'reported': 0, 'confirmed': 1, 'confirmed_undelivered': 2, 'awaiting_payment': 3, 'not_found': 4, 'verifying': 6, 'exception': 7, 'hold': 8, 'selection_finalized': 9, 'partially_refunded': 0, 'charged_back': 0, 'duplicate_review': 0, 'processing': 6, 'rejected': 7, 'canceled': 8, 'expired': 8, 'refunded': 8}.get` | ver matriz |
| `backend/app/main.py:14829` / `retry_payment_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:14830` / `retry_payment_notification` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:14875` / `client_pending_order` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:15017` / `favorite_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:15025` / `favorite_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:15053` / `unfavorite_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:15078` / `create_photo_comment` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:15086` / `create_photo_comment` | X | produtor | `PhotoComment` | ver matriz |
| `backend/app/main.py:15093` / `create_photo_comment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:15107` / `client_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:15131` / `remove_own_comment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:15151` / `admin_comments` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:15155` / `admin_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:15179` / `remove_comment_as_admin` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:15181` / `remove_comment_as_admin` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1085` / `db_session` | X | gate | `domain_session` | ver matriz |
| `backend/app/main.py:1103` / `require_installation_operator` | X | gate | `require_operator` | ver matriz |
| `backend/app/main.py:1109` / `directory_tenant_id` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1266` / `_client_journey_destination` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1269` / `_client_journey_destination` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1283` / `_client_journey_destination` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1297` / `_client_journey_destination` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1332` / `whatsapp_webhook` | X | gate | `webhook_owner` | ver matriz |
| `backend/app/main.py:1357` / `admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1393` / `provision_admin_whatsapp_channel` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1399` / `provision_admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1565` / `validate_client_capability_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1589` / `client_challenge_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1602` / `client_challenge_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1657` / `_client_has_verified_phone` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1782` / `client_challenge` | X | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/main.py:1807` / `client_resend` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1847` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1915` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2060` / `client_verify` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:2119` / `admin_password` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:2154` / `admin_totp` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:2162` / `admin_totp` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2217` / `issue_admin_totp_recovery_codes` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2322` / `admin_recovery_resend` | X | efeito potencial | `resend_security_challenge` | ver matriz |
| `backend/app/main.py:2373` / `admin_recovery_reset` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2383` / `admin_recovery_reset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2394` / `admin_recovery_reset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2451` / `confirm_admin_email` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2507` / `authenticated_identity` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2537` / `logout` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2538` / `logout` | X | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/main.py:2541` / `logout` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2575` / `admin_email_channel` | X | efeito potencial | `func.replace` | ver matriz |
| `backend/app/main.py:2606` / `admin_security_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2793` / `admin_email_change_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2858` / `_branding_payload` | X | query/ORM | `payload.update` | ver matriz |
| `backend/app/main.py:2920` / `update_visual_protection` | X | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/main.py:2923` / `update_visual_protection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2946` / `upload_branding_asset` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:2991` / `public_branding_asset` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:3043` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3056` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3059` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3065` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3077` / `admin_validation_summary` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:3257` / `_credit_owner_mutation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3315` / `_credit_owner_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3410` / `_owner_credit_catalog_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3557` / `admin_photo_credit_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3860` / `create_client` | X | produtor | `ClientPhone` | ver matriz |
| `backend/app/main.py:4021` / `_client_deletion_transaction_state` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4157` / `_gallery_cover_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4236` / `_local_cover_thumbnail_parent_ids` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4385` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4398` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4406` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4523` / `update_parent_gallery_settings` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4551` / `parent_gallery_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4560` / `parent_gallery_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4635` / `set_parent_gallery_cover` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4732` / `parent_gallery_details` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4735` / `parent_gallery_details` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4738` / `parent_gallery_details` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4819` / `register_parent_gallery_cover_photo` | X | produtor | `PhotoAsset` | ver matriz |
| `backend/app/main.py:4828` / `register_parent_gallery_cover_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4864` / `prepare_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4895` / `activate_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4934` / `suspend_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4959` / `revoke_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5070` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5075` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5089` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5097` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5234` / `admin_parent_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5262` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5348` / `admin_parent_gallery_folders` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5351` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5364` / `admin_parent_gallery_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5387` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5526` / `admin_client_restricted_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5538` / `admin_client_restricted_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5543` / `admin_client_restricted_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5597` / `create_admin_client_restricted_folder` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:5601` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5619` / `create_admin_client_restricted_folder` | X | produtor | `FolderClientGrant` | ver matriz |
| `backend/app/main.py:5665` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5672` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5682` / `grant_restricted_folder_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5728` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5890` / `delete_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5923` / `admin_photo_folder_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5943` / `admin_photo_folder_photos` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6055` / `_delete_photo_records` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6122` / `delete_folder_photo_assets` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6182` / `register_folder_photo_asset` | X | efeito potencial | `namespaced_upload_key` | ver matriz |
| `backend/app/main.py:6184` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6198` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6257` / `register_folder_photo_asset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6289` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6403` / `publish_parent_gallery_ready_photos` | X | efeito potencial | `can_publish_gallery` | ver matriz |
| `backend/app/main.py:6406` / `publish_parent_gallery_ready_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6416` / `publish_parent_gallery_ready_photos` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:6768` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:6870` / `parent_gallery_client_unlink_inventory` | X | efeito potencial | `client_unlink_inventory` | ver matriz |
| `backend/app/main.py:7029` / `cancel_gallery_lifecycle_operation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7069` / `clone_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7142` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7149` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7154` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7239` / `parent_gallery_clients` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7269` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7287` / `parent_gallery_clients` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:7339` / `parent_gallery_clients` | X | query/ORM | `clients_by_id.get` | ver matriz |
| `backend/app/main.py:7340` / `parent_gallery_clients` | X | query/ORM | `galleries_by_client.get` | ver matriz |
| `backend/app/main.py:7341` / `parent_gallery_clients` | X | query/ORM | `memberships_by_client.get` | ver matriz |
| `backend/app/main.py:7342` / `parent_gallery_clients` | X | query/ORM | `registrations_by_client.get` | ver matriz |
| `backend/app/main.py:7353` / `parent_gallery_clients` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:7355` / `parent_gallery_clients` | X | query/ORM | `phone_verification_by_client.get` | ver matriz |
| `backend/app/main.py:7366` / `parent_gallery_clients` | X | query/ORM | `latest_canonical_order_by_client.get` | ver matriz |
| `backend/app/main.py:7378` / `parent_gallery_clients` | X | query/ORM | `last_access_by_client.get` | ver matriz |
| `backend/app/main.py:7469` / `update_admin_client_gallery_access` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:7475` / `update_admin_client_gallery_access` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:7608` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7616` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7624` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7665` / `selection_detail` | X | query/ORM | `photos_by_id.get` | ver matriz |
| `backend/app/main.py:7827` / `_selection_html_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7840` / `_selection_html_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7937` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7981` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8036` / `export_canonical_selection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8108` / `export_canonical_selection` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8247` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8385` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8466` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8467` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8532` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8569` / `admin_photo_facial_analysis` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8664` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8690` / `admin_purchase_history` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8762` / `_pricing_preset_payload` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8844` / `create_progressive_pricing_preset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:8937` / `simulate_progressive_pricing_preset` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8982` / `pricing_payload` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9198` / `save_admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9216` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9371` / `issue_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9388` / `rotate_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9425` / `rotate_private_gallery_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9440` / `revoke_private_gallery_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9456` / `_private_member_payload` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9576` / `add_private_gallery_member` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9581` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9638` / `add_private_gallery_member` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:9709` / `_change_private_member_status` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:9733` / `block_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9752` / `unblock_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9771` / `unlink_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9809` / `admin_gallery_membership_notifications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9877` / `list_admin_media_archive_notices` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9909` / `_media_archive_notice_timestamp` | X | efeito potencial | `value.replace` | ver matriz |
| `backend/app/main.py:10053` / `admin_private_gallery_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10290` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10347` / `add_admin_private_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10377` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10388` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10403` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:10406` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10414` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:10448` / `delete_derived_gallery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10471` / `gallery_operational_status` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10473` / `gallery_operational_status` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10483` / `gallery_operational_status` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10524` / `list_derived_galleries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10530` / `list_derived_galleries` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10541` / `list_derived_galleries` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10582` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10588` / `derived_gallery_detail` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10599` / `derived_gallery_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10684` / `_reopening_request_payload` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10736` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10894` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10904` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10950` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:10953` / `client_library` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:10973` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10995` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:10998` / `client_library` | X | query/ORM | `registrations_by_parent.get` | ver matriz |
| `backend/app/main.py:11050` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11059` / `client_library` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:11071` / `client_library` | X | query/ORM | `prepared_gallery_ids.update` | ver matriz |
| `backend/app/main.py:11081` / `client_library` | X | query/ORM | `prepared_gallery_ids.update` | ver matriz |
| `backend/app/main.py:11124` / `client_library` | X | query/ORM | `public_by_parent.get` | ver matriz |
| `backend/app/main.py:11125` / `client_library` | X | query/ORM | `private_by_parent.get` | ver matriz |
| `backend/app/main.py:11146` / `client_library` | X | query/ORM | `canonical_cart_groups.get` | ver matriz |
| `backend/app/main.py:11156` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:11297` / `remove_unified_cart_group` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11342` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11427` / `client_purchase_history` | X | query/ORM | `operational_galleries.get` | ver matriz |
| `backend/app/main.py:11428` / `client_purchase_history` | X | query/ORM | `canonical_parents.get` | ver matriz |
| `backend/app/main.py:11532` / `client_purchase_history` | X | query/ORM | `order_payload.get` | ver matriz |
| `backend/app/main.py:11712` / `gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11820` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11847` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11855` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11863` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12105` / `client_photo_preview` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:12145` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12238` / `_operational_gallery_for_public_client` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:12776` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12792` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12809` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12844` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12949` / `public_gallery_photo_preview` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:13016` / `favorite_canonical_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13046` / `unfavorite_canonical_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:13070` / `record_canonical_photo_view` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13202` / `unselect_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:13203` / `unselect_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13262` / `_client_folder_for_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13359` / `_create_folder_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13391` / `_create_folder_reopening_request` | X | produtor | `GalleryReopeningNotificationOutbox` | ver matriz |
| `backend/app/main.py:13735` / `correct_payment_confirmation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:13755` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13855` / `resend_order_delivery` | X | efeito potencial | `resend_delivery` | ver matriz |
| `backend/app/main.py:13896` / `register_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:13922` / `unregister_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:14192` / `_payment_dashboard_data` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:14203` / `_payment_dashboard_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14217` / `_payment_dashboard_data` | X | query/ORM | `scopes.get` | ver matriz |
| `backend/app/main.py:14392` / `_payment_dashboard_data` | X | query/ORM | `communications_by_order.get` | ver matriz |
| `backend/app/main.py:14399` / `_payment_dashboard_data` | X | query/ORM | `card_payments.get` | ver matriz |
| `backend/app/main.py:14400` / `_payment_dashboard_data` | X | query/ORM | `mp_payments.get` | ver matriz |
| `backend/app/main.py:14431` / `_payment_dashboard_data` | X | query/ORM | `items_by_order.get` | ver matriz |
| `backend/app/main.py:14898` / `client_pending_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:15033` / `favorite_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:15061` / `unfavorite_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:15153` / `admin_comments` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:586` / `validate_branding_asset` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:1343` / `whatsapp_admin_payload` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:1435` / `refresh_admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1448` / `pair_admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1486` / `admin_whatsapp_deliveries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1517` / `retry_admin_whatsapp_delivery` | X | efeito potencial | `updated_at.replace` | ver matriz |
| `backend/app/main.py:1712` / `client_challenge` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:2254` / `issue_admin_totp_recovery_codes` | X | produtor | `AdminTotpRecoveryCode` | ver matriz |
| `backend/app/main.py:2576` / `admin_email_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2581` / `admin_email_channel` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:2605` / `admin_security_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2650` / `admin_global_pix_challenge` | X | query/ORM | `configuration.get` | ver matriz |
| `backend/app/main.py:2919` / `update_visual_protection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3134` / `summary_timestamp` | X | efeito potencial | `value.replace` | ver matriz |
| `backend/app/main.py:3247` / `_credit_owner_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3272` / `_credit_owner_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3300` / `_credit_owner_mutation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3304` / `_credit_owner_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3353` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3374` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3393` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3397` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3912` / `delete_client` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:4070` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4073` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4079` / `parent_gallery_overview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4909` / `activate_parent_gallery_facial_policy` | X | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/main.py:5277` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5380` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5399` / `admin_parent_gallery_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5440` / `admin_parent_gallery_folders` | X | query/ORM | `client_names_by_folder.get` | ver matriz |
| `backend/app/main.py:5677` / `grant_restricted_folder_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5682` / `grant_restricted_folder_client` | X | produtor | `FolderClientGrant` | ver matriz |
| `backend/app/main.py:6097` / `_remove_photo_files` | X | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/main.py:6216` / `register_folder_photo_asset` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6224` / `register_folder_photo_asset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6228` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6257` / `register_folder_photo_asset` | X | produtor | `PrivateUploadBatchAsset` | ver matriz |
| `backend/app/main.py:6281` / `_publish_photo_folder` | X | efeito potencial | `can_publish_gallery` | ver matriz |
| `backend/app/main.py:6285` / `_publish_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6293` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6314` / `_publish_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6331` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6341` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6781` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:6900` / `delete_parent_gallery` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:7033` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `(operation.manifest or {}).get` | ver matriz |
| `backend/app/main.py:7034` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7181` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7199` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7203` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7228` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7305` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7343` / `parent_gallery_clients` | X | query/ORM | `projections.get` | ver matriz |
| `backend/app/main.py:7354` / `parent_gallery_clients` | X | query/ORM | `canonical_selected.get` | ver matriz |
| `backend/app/main.py:7367` / `parent_gallery_clients` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:7428` / `link_admin_client_to_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7500` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:7636` / `selection_detail` | X | query/ORM | `sales_by_photo.get` | ver matriz |
| `backend/app/main.py:7752` / `_purchase_photo_interactions` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7780` / `_purchase_photo_interactions` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7834` / `_selection_html_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7925` / `export_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8045` / `export_canonical_selection` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8265` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8300` / `import_photo_source` | X | efeito potencial | `photographer_credits.record_upload_attempt` | ver matriz |
| `backend/app/main.py:8674` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8692` / `admin_purchase_history` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8802` / `_replace_pricing_preset_tiers` | X | produtor | `ProgressivePricingTier` | ver matriz |
| `backend/app/main.py:8821` / `list_progressive_pricing_presets` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9128` / `save_parent_pricing` | X | produtor | `PriceRule` | ver matriz |
| `backend/app/main.py:9225` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9466` / `_private_member_payload` | X | efeito potencial | `membership.unlinked_at.isoformat` | ver matriz |
| `backend/app/main.py:9515` / `private_gallery_members` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:9799` / `admin_gallery_membership_notifications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9864` / `list_admin_media_archive_notices` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10139` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10146` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10166` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10176` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10192` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10202` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10307` / `admin_private_gallery_photos` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:10382` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10389` / `remove_admin_private_gallery_photo` | X | produtor | `DerivedGalleryPhotoOrigin` | ver matriz |
| `backend/app/main.py:10474` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10478` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10546` / `list_derived_galleries` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10732` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10808` / `decide_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10936` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10941` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11108` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11127` / `client_library` | X | query/ORM | `galleries_by_id.get` | ver matriz |
| `backend/app/main.py:11143` / `client_library` | X | query/ORM | `carts_by_gallery.get` | ver matriz |
| `backend/app/main.py:11150` / `client_library` | X | query/ORM | `orders_by_gallery.get` | ver matriz |
| `backend/app/main.py:11152` / `client_library` | X | query/ORM | `canonical_orders_by_parent.get` | ver matriz |
| `backend/app/main.py:11377` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11391` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11406` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11416` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11431` / `client_purchase_history` | X | query/ORM | `history_by_item.get` | ver matriz |
| `backend/app/main.py:11780` / `gallery_released_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12061` / `client_photo_preview` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:12106` / `client_photo_preview` | X | produtor | `PhotoView` | ver matriz |
| `backend/app/main.py:12552` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:12560` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:12862` / `public_gallery_photos` | X | query/ORM | `folder_counts.get` | ver matriz |
| `backend/app/main.py:13016` / `favorite_canonical_photo` | X | produtor | `PhotoFavorite` | ver matriz |
| `backend/app/main.py:13070` / `record_canonical_photo_view` | X | produtor | `PhotoView` | ver matriz |
| `backend/app/main.py:13371` / `_create_folder_reopening_request` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:13377` / `_create_folder_reopening_request` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:13648` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13697` / `decide_payment_communication` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13803` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:13996` / `list_payment_templates` | X | query/ORM | `configured.get` | ver matriz |
| `backend/app/main.py:14223` / `_payment_dashboard_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14243` / `_payment_dashboard_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14264` / `_payment_dashboard_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14324` / `_payment_dashboard_data` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:14357` / `_payment_dashboard_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14426` / `_payment_dashboard_data` | X | query/ORM | `scopes_by_communication.get` | ver matriz |
| `backend/app/main.py:14432` / `_payment_dashboard_data` | X | query/ORM | `purchase_interactions.get` | ver matriz |
| `backend/app/main.py:14627` / `_payment_dashboard_data` | X | query/ORM | `configured_templates.get` | ver matriz |
| `backend/app/main.py:14804` / `_decode_payment_cursor` | X | query/ORM | `payload.get` | ver matriz |
| `backend/app/main.py:14953` / `client_pending_order` | X | query/ORM | `photos_by_id.get` | ver matriz |
| `backend/app/main.py:14957` / `client_pending_order` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:14959` / `client_pending_order` | X | query/ORM | `folder_expiries.get` | ver matriz |
| `backend/app/main.py:15034` / `favorite_photo` | X | produtor | `PhotoFavorite` | ver matriz |
| `backend/app/main.py:1378` / `provision_admin_whatsapp_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1561` / `validate_client_capability_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1607` / `client_challenge_context` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1648` / `_purchase_return_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1668` / `_active_client_reauthentication_parent` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1885` / `client_verify` | X | produtor | `Client` | ver matriz |
| `backend/app/main.py:1890` / `client_verify` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:1892` / `client_verify` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:1922` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2107` / `admin_password` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2124` / `admin_password` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2130` / `admin_password` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2179` / `admin_totp` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2285` / `admin_recovery_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2368` / `admin_recovery_reset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2376` / `admin_recovery_reset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2446` / `confirm_admin_email` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2459` / `confirm_admin_email` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2513` / `authenticated_identity` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3010` / `public_branding_asset` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:3039` / `admin_validation_summary` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:3147` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3150` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3157` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3160` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3247` / `_credit_owner_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3267` / `_credit_owner_mutation` | X | efeito potencial | `action.replace` | ver matriz |
| `backend/app/main.py:3272` / `_credit_owner_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3304` / `_credit_owner_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3353` / `_owner_credit_catalog_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3369` / `_owner_credit_catalog_mutation` | X | efeito potencial | `action.replace` | ver matriz |
| `backend/app/main.py:3374` / `_owner_credit_catalog_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3397` / `_owner_credit_catalog_mutation` | X | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/main.py:3607` / `admin_create_credit_package` | X | query/ORM | `session_db.get` | ver matriz |
| `backend/app/main.py:3632` / `admin_update_credit_package` | X | query/ORM | `session_db.get` | ver matriz |
| `backend/app/main.py:3737` / `admin_review_credit_purchase` | X | query/ORM | `session_db.get` | ver matriz |
| `backend/app/main.py:3787` / `admin_installation_capabilities` | X | gate | `operator_is_active` | ver matriz |
| `backend/app/main.py:3885` / `update_client_name` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4081` / `parent_gallery_overview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4278` / `_local_cover_thumbnail_parent_ids` | X | query/ORM | `latest_states.get` | ver matriz |
| `backend/app/main.py:4288` / `_admin_photo_preview_available` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5288` / `admin_parent_gallery_available_photos` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:5292` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5677` / `grant_restricted_folder_client` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:5689` / `grant_restricted_folder_client` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5733` / `revoke_restricted_folder_client` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:5784` / `renew_public_photo_folder_deadline` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5902` / `delete_photo_folder` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:5920` / `admin_photo_folder_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6074` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6075` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6178` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6224` / `register_folder_photo_asset` | X | produtor | `PrivateUploadBatchAsset` | ver matriz |
| `backend/app/main.py:7041` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `previous_state.get` | ver matriz |
| `backend/app/main.py:7087` / `challenge_client_phone` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7107` / `change_client_phone` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7233` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7249` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7260` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7295` / `parent_gallery_clients` | X | query/ORM | `canonical_item_counts.get` | ver matriz |
| `backend/app/main.py:7299` / `parent_gallery_clients` | X | query/ORM | `canonical_group_scopes.get` | ver matriz |
| `backend/app/main.py:7562` / `unlink_admin_client_from_parent_gallery` | X | efeito potencial | `client_unlink_inventory` | ver matriz |
| `backend/app/main.py:7646` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7668` / `selection_detail` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:7800` / `_purchase_photo_interactions` | X | query/ORM | `latest_comments.get` | ver matriz |
| `backend/app/main.py:8196` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:8248` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:8324` / `import_photo_source` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:8552` / `photo_media_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8668` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8795` / `_replace_pricing_preset_tiers` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:8825` / `list_progressive_pricing_presets` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9050` / `save_parent_pricing` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9125` / `save_parent_pricing` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:9683` / `_change_private_member_status` | X | efeito potencial | `unlink_private_membership` | ver matriz |
| `backend/app/main.py:10015` / `list_restricted_folder_upload_batches` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10063` / `admin_private_gallery_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10077` / `admin_private_gallery_folders` | X | query/ORM | `counts.get` | ver matriz |
| `backend/app/main.py:10245` / `admin_private_gallery_photos` | X | query/ORM | `state_priority.get` | ver matriz |
| `backend/app/main.py:10324` / `admin_private_gallery_photos` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:10679` / `_reopening_request_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10745` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10754` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10761` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10773` / `list_gallery_reopening_requests` | X | query/ORM | `requesters.get` | ver matriz |
| `backend/app/main.py:10923` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11133` / `client_library` | X | query/ORM | `public_row.get` | ver matriz |
| `backend/app/main.py:11138` / `client_library` | X | query/ORM | `private_row.get` | ver matriz |
| `backend/app/main.py:11368` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11435` / `client_purchase_history` | X | query/ORM | `media_state_by_folder.get` | ver matriz |
| `backend/app/main.py:11571` / `_historical_item_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11729` / `gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11873` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12782` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12798` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12823` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12836` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:13876` / `push_subscription_state` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14049` / `admin_order_item_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14051` / `admin_order_item_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14058` / `admin_order_item_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14069` / `admin_order_item_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14198` / `_payment_dashboard_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14397` / `_payment_dashboard_data` | X | query/ORM | `notifications_by_communication.get` | ver matriz |
| `backend/app/main.py:14439` / `_payment_dashboard_data` | X | query/ORM | `media_state_cache.get` | ver matriz |
| `backend/app/main.py:14906` / `client_pending_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14923` / `client_pending_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:14963` / `client_pending_order` | X | query/ORM | `selection_created_at_by_photo.get` | ver matriz |
| `backend/app/main.py:1266` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1270` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1284` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1565` / `validate_client_capability_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1657` / `_client_has_verified_phone` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1893` / `client_verify` | X | produtor | `ClientPhone` | ver matriz |
| `backend/app/main.py:1972` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2394` / `admin_recovery_reset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2403` / `admin_recovery_reset` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2541` / `logout` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2576` / `admin_email_channel` | X | efeito potencial | `func.replace` | ver matriz |
| `backend/app/main.py:2794` / `admin_email_change_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2924` / `update_visual_protection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3043` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3057` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3060` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3062` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3142` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3257` / `_credit_owner_mutation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3557` / `admin_photo_credit_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3798` / `admin_capacity_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:4141` / `_active_gallery_capability` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4236` / `_local_cover_thumbnail_parent_ids` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5090` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5098` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5556` / `admin_client_restricted_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5951` / `admin_photo_folder_photos` | X | query/ORM | `fingerprints.get` | ver matriz |
| `backend/app/main.py:6055` / `_delete_photo_records` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6184` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6324` / `_publish_photo_folder` | X | efeito potencial | `enqueue_photo_index_if_eligible` | ver matriz |
| `backend/app/main.py:7047` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `previous_state.get` | ver matriz |
| `backend/app/main.py:7276` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7395` / `parent_gallery_clients` | X | query/ORM | `canonical_purchased.get` | ver matriz |
| `backend/app/main.py:7398` / `parent_gallery_clients` | X | query/ORM | `canonical_reopening.get` | ver matriz |
| `backend/app/main.py:7401` / `parent_gallery_clients` | X | query/ORM | `finalized_by_client.get` | ver matriz |
| `backend/app/main.py:7402` / `parent_gallery_clients` | X | query/ORM | `canonical_financial_by_client.get` | ver matriz |
| `backend/app/main.py:7682` / `selection_detail` | X | query/ORM | `sales_by_photo.get` | ver matriz |
| `backend/app/main.py:7796` / `_purchase_photo_interactions` | X | query/ORM | `favorited_keys.add` | ver matriz |
| `backend/app/main.py:8067` / `export_canonical_selection` | X | query/ORM | `interactions_by_item.get` | ver matriz |
| `backend/app/main.py:8331` / `import_photo_source` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:8475` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8508` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8659` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10246` / `admin_private_gallery_photos` | X | query/ORM | `commercial_state_by_photo_client.get` | ver matriz |
| `backend/app/main.py:10267` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:10275` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:10283` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:10306` / `admin_private_gallery_photos` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:10308` / `admin_private_gallery_photos` | X | query/ORM | `origins_by_reference.get` | ver matriz |
| `backend/app/main.py:10471` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10473` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10483` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10685` / `_reopening_request_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11073` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:11083` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:11548` / `client_purchase_history` | X | query/ORM | `item.get` | ver matriz |
| `backend/app/main.py:12155` / `select_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:12582` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:12849` / `public_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:13263` / `_client_folder_for_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13264` / `_client_folder_for_reopening` | X | gate | `client_tenant_id` | ver matriz |
| `backend/app/main.py:14422` / `_payment_dashboard_data` | X | query/ORM | `notifications_by_communication.get` | ver matriz |
| `backend/app/main.py:14423` / `_payment_dashboard_data` | X | query/ORM | `corrections_by_communication.get` | ver matriz |
| `backend/app/main.py:14547` / `_payment_dashboard_data` | X | query/ORM | `(order_payload.get('mercadopago') or {}).get` | ver matriz |
| `backend/app/main.py:14601` / `_payment_dashboard_data` | X | query/ORM | `(order_payload.get('mercadopago') or {}).get` | ver matriz |
| `backend/app/main.py:1216` / `assigned_photo_for_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1614` / `client_challenge_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1998` / `client_verify` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:2148` / `admin_totp` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2247` / `issue_admin_totp_recovery_codes` | X | query/ORM | `update` | ver matriz |
| `backend/app/main.py:2521` / `authenticated_identity` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2646` / `admin_global_pix_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2684` / `admin_global_pix_confirm` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2685` / `admin_global_pix_confirm` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2919` / `update_visual_protection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3240` / `_credit_owner_mutation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3346` / `_owner_credit_catalog_mutation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4181` / `_cover_preview_url` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4316` / `_cover_derivative` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4325` / `_client_preview_derivative` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4350` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4359` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4611` / `set_parent_gallery_cover` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4660` / `clear_parent_gallery_cover` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4798` / `register_parent_gallery_cover_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4812` / `register_parent_gallery_cover_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5462` / `create_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5470` / `create_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5504` / `_admin_linked_gallery_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5605` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5660` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5722` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5836` / `configure_photo_folder_deadline` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5935` / `admin_photo_folder_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5986` / `delete_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6065` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6066` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6067` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6068` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6069` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6073` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6077` / `_delete_photo_records` | X | query/ORM | `update` | ver matriz |
| `backend/app/main.py:6193` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6217` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6228` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6314` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6331` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7204` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7391` / `parent_gallery_clients` | X | query/ORM | `restricted_available.get` | ver matriz |
| `backend/app/main.py:7781` / `_purchase_photo_interactions` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7856` / `_selection_html_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7873` / `_selection_html_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7976` / `export_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8032` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8197` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8203` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8265` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8386` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:8557` / `photo_media_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8600` / `admin_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8630` / `admin_watermarked_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8728` / `admin_purchase_history` | X | query/ORM | `items_by_order.get` | ver matriz |
| `backend/app/main.py:9262` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9341` / `private_gallery_link_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9924` / `read_admin_media_archive_notice` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9996` / `begin_restricted_folder_upload_batch` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10022` / `list_restricted_folder_upload_batches` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10104` / `create_private_gallery_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10256` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:10323` / `admin_private_gallery_photos` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:10370` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10397` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10870` / `retry_gallery_reopening_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11194` / `client_library` | X | query/ORM | `canonical_orders_by_parent.get` | ver matriz |
| `backend/app/main.py:11281` / `remove_unified_cart_group` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11311` / `remove_unified_cart_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11545` / `client_purchase_history` | X | query/ORM | `item.get` | ver matriz |
| `backend/app/main.py:11545` / `client_purchase_history` | X | query/ORM | `item.get` | ver matriz |
| `backend/app/main.py:11558` / `_historical_item_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11996` / `_client_photo_preview_is_available` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12127` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12155` / `select_photo` | X | produtor | `PhotoSelection` | ver matriz |
| `backend/app/main.py:12159` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12267` / `unselect_photo_from_public_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12403` / `public_gallery_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13010` / `favorite_canonical_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13040` / `unfavorite_canonical_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13062` / `record_canonical_photo_view` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13147` / `remove_canonical_comment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13285` / `_latest_folder_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13338` / `_create_folder_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13579` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13729` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14285` / `_payment_dashboard_data` | X | query/ORM | `items_by_order.get` | ver matriz |
| `backend/app/main.py:14876` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:15026` / `favorite_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:15054` / `unfavorite_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:15132` / `remove_own_comment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:15182` / `remove_comment_as_admin` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1109` / `directory_tenant_id` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1393` / `provision_admin_whatsapp_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1471` / `admin_whatsapp_deliveries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1589` / `client_challenge_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1602` / `client_challenge_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2162` / `admin_totp` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2217` / `issue_admin_totp_recovery_codes` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2606` / `admin_security_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3147` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3150` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3157` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3160` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3249` / `_credit_owner_mutation` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:3274` / `_credit_owner_mutation` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:3306` / `_credit_owner_mutation` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:4022` / `_client_deletion_transaction_state` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4523` / `update_parent_gallery_settings` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4552` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4636` / `set_parent_gallery_cover` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4738` / `parent_gallery_details` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5071` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5076` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5538` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5672` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5728` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5943` / `admin_photo_folder_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6198` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6289` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7143` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7150` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7155` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7322` / `parent_gallery_clients` | X | query/ORM | `finalized_media_states.get` | ver matriz |
| `backend/app/main.py:7609` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7617` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7647` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7841` / `_selection_html_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8247` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8467` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8668` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8715` / `admin_purchase_history` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:8763` / `_pricing_preset_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8938` / `simulate_progressive_pricing_preset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8983` / `pricing_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9577` / `add_private_gallery_member` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9878` / `list_admin_media_archive_notices` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10291` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10378` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10407` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10524` / `list_derived_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10600` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10746` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10917` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11297` / `remove_unified_cart_group` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11368` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11708` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11762` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11816` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12146` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12542` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:13204` / `unselect_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13360` / `_create_folder_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14198` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14907` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14924` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1232` / `assigned_photo_for_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1991` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:3234` / `_credit_owner_mutation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3341` / `_owner_credit_catalog_mutation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3355` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:3376` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:3399` / `_owner_credit_catalog_mutation` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:4038` / `admin_parent_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4065` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4070` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4074` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4249` / `_local_cover_thumbnail_parent_ids` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4348` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5237` / `admin_parent_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5278` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5589` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5592` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5647` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5712` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5713` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5736` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5793` / `renew_public_photo_folder_deadline` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5797` / `renew_public_photo_folder_deadline` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5878` / `delete_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5991` / `delete_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6024` / `_assert_photo_credit_operations_settled` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6070` / `_delete_photo_records` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6072` / `_delete_photo_records` | X | query/ORM | `update` | ver matriz |
| `backend/app/main.py:6150` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6294` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6342` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6855` / `parent_gallery_client_unlink_inventory` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6907` / `delete_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6970` / `retry_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6999` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7035` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7199` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7228` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7332` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7458` / `update_admin_client_gallery_access` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7464` / `update_admin_client_gallery_access` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7507` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7538` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7753` / `_purchase_photo_interactions` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8003` / `export_finalized_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8508` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8675` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9225` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9514` / `private_gallery_members` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9948` / `list_private_upload_batches` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10383` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10436` / `delete_derived_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10578` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10792` / `decide_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10809` / `decide_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10937` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10942` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11392` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11407` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11417` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11590` / `client_purchased_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12012` / `_client_photo_preview_is_available` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12062` / `client_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12083` / `client_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12096` / `client_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12965` / `public_gallery_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13125` / `canonical_client_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13588` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13615` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13649` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13698` / `decide_payment_communication` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13741` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13748` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13804` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14547` / `_payment_dashboard_data` | X | query/ORM | `order_payload.get` | ver matriz |
| `backend/app/main.py:14601` / `_payment_dashboard_data` | X | query/ORM | `order_payload.get` | ver matriz |
| `backend/app/main.py:15108` / `client_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:15156` / `admin_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2383` / `admin_recovery_reset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3040` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4386` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4399` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4407` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5293` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5352` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5365` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5665` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5689` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5924` / `admin_photo_folder_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5936` / `admin_photo_folder_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6407` / `publish_parent_gallery_ready_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7239` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7269` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7625` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8036` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8385` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8725` / `admin_purchase_history` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:9051` / `save_parent_pricing` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9217` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10054` / `admin_private_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10448` / `delete_derived_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10542` / `list_derived_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10589` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10755` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10761` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10895` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10905` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10924` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11050` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11192` / `client_library` | X | query/ORM | `cart.get` | ver matriz |
| `backend/app/main.py:11343` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11497` / `client_purchase_history` | X | query/ORM | `communications_by_order.get` | ver matriz |
| `backend/app/main.py:11848` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11856` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11864` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12776` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12792` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:13756` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14203` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14899` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1344` / `whatsapp_admin_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2403` / `admin_recovery_reset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2582` / `admin_email_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3142` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3300` / `_credit_owner_mutation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3393` / `_owner_credit_catalog_mutation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4195` / `_archive_object_state` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4578` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5381` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5556` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6286` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6923` / `delete_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7182` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7305` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7327` / `parent_gallery_clients` | X | query/ORM | `finalized_media_states.get` | ver matriz |
| `backend/app/main.py:7528` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8231` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8720` / `admin_purchase_history` | X | query/ORM | `media_states.get` | ver matriz |
| `backend/app/main.py:10167` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10177` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10193` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11074` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11378` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12850` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14224` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14244` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14265` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14358` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2179` / `admin_totp` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3045` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3065` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4561` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5263` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5526` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5890` / `delete_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7233` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8109` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10064` / `admin_private_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10257` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11730` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11874` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12159` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12783` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12799` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12824` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12837` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5400` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7276` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7926` / `export_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8046` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9865` / `list_admin_media_archive_notices` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10147` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11084` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11109` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11350` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11353` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11781` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5388` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5543` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7260` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9263` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14158` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4161` / `_gallery_cover_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10140` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10203` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11766` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7249` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10974` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11713` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11821` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:14295` / `_payment_dashboard_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9516` / `private_gallery_members` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3078` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/media.py:43` / `safe_source_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:49` / `safe_source_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:70` / `safe_source_path_from_credit_snapshot` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:78` / `safe_derivative_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:84` / `safe_derivative_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:142` / `_watermark_font_size` | P | query/ORM | `{'horizontal': inner_width, 'vertical': inner_height, 'diagonal': hypot(inner_width, inner_height)}.get` | ver matriz |
| `backend/app/media.py:181` / `watermark` | P | query/ORM | `{'horizontal': 0, 'vertical': 90, 'diagonal': 35}.get` | ver matriz |
| `backend/app/media.py:191` / `watermark` | P | query/ORM | `{'sans-serif': 'DejaVuSans.ttf', 'serif': 'DejaVuSerif.ttf', 'monospace': 'DejaVuSansMono.ttf', 'DejaVuSans': 'DejaVuSans.ttf', 'DejaVuSerif': 'DejaVuSerif.ttf'}.get` | ver matriz |
| `backend/app/media.py:244` / `watermark` | P | query/ORM | `layer_draw.text` | ver matriz |
| `backend/app/media.py:249` / `watermark` | P | query/ORM | `{'left': margin, 'center': (marked.width - layer.width) // 2, 'right': marked.width - layer.width - margin}.get` | ver matriz |
| `backend/app/media.py:254` / `watermark` | P | query/ORM | `{'top': margin, 'middle': (marked.height - layer.height) // 2, 'bottom': marked.height - layer.height - margin}.get` | ver matriz |
| `backend/app/media.py:267` / `require_media_photo` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:298` / `enqueue_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:299` / `enqueue_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:325` / `generate_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:469` / `save_presentation_jpeg` | P | efeito potencial | `destination.write_bytes` | ver matriz |
| `backend/app/media.py:238` / `watermark` | P | query/ORM | `layer_draw.text` | ver matriz |
| `backend/app/media.py:268` / `require_media_photo` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:277` / `require_media_photo` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:282` / `require_media_photo` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:305` / `enqueue_derivatives` | P | produtor | `MediaJob` | ver matriz |
| `backend/app/media.py:306` / `enqueue_derivatives` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/media.py:328` / `generate_derivatives` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:336` / `generate_derivatives` | P | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/media.py:343` / `generate_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:357` / `generate_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:403` / `generate_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:407` / `generate_derivatives` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:442` / `generate_derivatives` | P | efeito potencial | `enqueue_after_derivatives` | ver matriz |
| `backend/app/media.py:311` / `enqueue_derivatives` | P | query/ORM | `db.get` | ver matriz |
| `backend/app/media.py:358` / `generate_derivatives` | P | efeito potencial | `Image.open` | ver matriz |
| `backend/app/media.py:412` / `generate_derivatives` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:433` / `generate_derivatives` | P | efeito potencial | `enqueue_photo_index_if_eligible` | ver matriz |
| `backend/app/media.py:300` / `enqueue_derivatives` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:375` / `generate_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:379` / `generate_derivatives` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:382` / `generate_derivatives` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:394` / `generate_derivatives` | P | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/media.py:413` / `generate_derivatives` | P | efeito potencial | `can_publish_gallery` | ver matriz |
| `backend/app/media.py:343` / `generate_derivatives` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:390` / `generate_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:396` / `generate_derivatives` | P | produtor | `MediaDerivative` | ver matriz |
| `backend/app/media.py:397` / `generate_derivatives` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/media.py:392` / `generate_derivatives` | P | efeito potencial | `temporary.unlink` | ver matriz |
| `backend/app/media.py:278` / `require_media_photo` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:357` / `generate_derivatives` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:375` / `generate_derivatives` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:269` / `require_media_photo` | P | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:64` / `recovery_pricing_payload` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_billing.py:67` / `recovery_pricing_payload` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_billing.py:82` / `owner_recovery_pricing` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_billing.py:107` / `update_recovery_pricing` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:120` / `update_recovery_pricing` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:132` / `update_recovery_pricing` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:148` / `_active_allocatable_sources` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_billing.py:177` / `_request_for_operation` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:192` / `failed_recovery_cycle_id` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:210` / `_request_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:214` / `_request_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:285` / `_append_recovery_event` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:331` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:379` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:387` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:400` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:433` / `request_recovery` | S | produtor | `MediaArchiveOperation` | ver matriz |
| `backend/app/media_archive_billing.py:450` / `request_recovery` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:452` / `request_recovery` | S | produtor | `MediaArchiveRecoveryRequest` | ver matriz |
| `backend/app/media_archive_billing.py:467` / `request_recovery` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:468` / `request_recovery` | S | produtor | `MediaArchiveRecoveryCreditReservation` | ver matriz |
| `backend/app/media_archive_billing.py:474` / `request_recovery` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:536` / `mark_recovery_uncertain` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:549` / `release_failed_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:584` / `consume_verified_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:633` / `consume_verified_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:641` / `consume_verified_recovery` | S | produtor | `PhotographerCreditEntry` | ver matriz |
| `backend/app/media_archive_billing.py:652` / `consume_verified_recovery` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:673` / `list_tenant_recoveries` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_billing.py:687` / `list_owner_recoveries` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_billing.py:45` / `_is_platform_owner_tenant` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_billing.py:111` / `update_recovery_pricing` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_billing.py:124` / `update_recovery_pricing` | S | produtor | `MediaArchiveRecoveryPricing` | ver matriz |
| `backend/app/media_archive_billing.py:125` / `update_recovery_pricing` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:132` / `update_recovery_pricing` | S | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/media_archive_billing.py:218` / `_request_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:240` / `_request_payload` | S | query/ORM | `payload.update` | ver matriz |
| `backend/app/media_archive_billing.py:285` / `_append_recovery_event` | S | produtor | `MediaArchiveEvent` | ver matriz |
| `backend/app/media_archive_billing.py:319` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:355` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:420` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:477` / `request_recovery` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:498` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:510` / `_active_recovery_allocations` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_billing.py:563` / `release_failed_recovery` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:608` / `consume_verified_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:655` / `consume_verified_recovery` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_billing.py:685` / `list_owner_recoveries` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_billing.py:171` / `_request_for_operation` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:251` / `list_recovery_candidates` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/media_archive_billing.py:371` / `request_recovery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_billing.py:477` / `request_recovery` | S | produtor | `MediaArchiveRecoveryCreditAllocationEvent` | ver matriz |
| `backend/app/media_archive_billing.py:563` / `release_failed_recovery` | S | produtor | `MediaArchiveRecoveryCreditAllocationEvent` | ver matriz |
| `backend/app/media_archive_billing.py:599` / `consume_verified_recovery` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_billing.py:613` / `consume_verified_recovery` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_billing.py:655` / `consume_verified_recovery` | S | produtor | `MediaArchiveRecoveryCreditAllocationEvent` | ver matriz |
| `backend/app/media_archive_billing.py:107` / `update_recovery_pricing` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:192` / `failed_recovery_cycle_id` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:210` / `_request_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:214` / `_request_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:331` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:387` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:400` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:600` / `consume_verified_recovery` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_billing.py:218` / `_request_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:319` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:498` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:120` / `update_recovery_pricing` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:371` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:379` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:536` / `mark_recovery_uncertain` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:549` / `release_failed_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:584` / `consume_verified_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:613` / `consume_verified_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:633` / `consume_verified_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:355` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:420` / `request_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:510` / `_active_recovery_allocations` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:608` / `consume_verified_recovery` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:148` / `_active_allocatable_sources` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:673` / `list_tenant_recoveries` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:687` / `list_owner_recoveries` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:45` / `_is_platform_owner_tenant` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_billing.py:251` / `list_recovery_candidates` | S | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:153` / `_load_operation_scope` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_executor.py:235` / `_verify_remote_object` | L | efeito potencial | `storage.download_object` | ver matriz |
| `backend/app/media_archive_executor.py:337` / `_safe_unlink_staging_file` | L | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/media_archive_executor.py:1390` / `_load_delete_operation_scope` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_executor.py:120` / `write` | L | query/ORM | `self._digest.update` | ver matriz |
| `backend/app/media_archive_executor.py:132` / `_as_utc` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/media_archive_executor.py:157` / `_load_operation_scope` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_executor.py:172` / `_object_rows` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_executor.py:209` / `_safe_source_stream` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:264` / `write` | L | query/ORM | `self._digest.update` | ver matriz |
| `backend/app/media_archive_executor.py:290` / `_local_file_digest` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:347` / `_exclusive_private_file` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:381` / `_download_verified_object` | L | efeito potencial | `_safe_unlink_staging_file` | ver matriz |
| `backend/app/media_archive_executor.py:385` / `_download_verified_object` | L | efeito potencial | `storage.download_object` | ver matriz |
| `backend/app/media_archive_executor.py:441` / `_fsync_directory` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:465` / `_promote_verified_object` | L | efeito potencial | `_safe_unlink_staging_file` | ver matriz |
| `backend/app/media_archive_executor.py:516` / `_promote_verified_object` | L | efeito potencial | `_safe_unlink_staging_file` | ver matriz |
| `backend/app/media_archive_executor.py:679` / `_unlink_verified` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:738` / `_unlink_verified` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:759` / `_unlink_verified` | L | efeito potencial | `target.unlink` | ver matriz |
| `backend/app/media_archive_executor.py:1069` / `_cleanup_local_media` | L | efeito potencial | `_unlink_verified` | ver matriz |
| `backend/app/media_archive_executor.py:1158` / `_assert_restore_space_is_reserved` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_executor.py:1247` / `execute_restore_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_executor.py:1397` / `_load_delete_operation_scope` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_executor.py:101` / `read` | L | query/ORM | `self._digest.update` | ver matriz |
| `backend/app/media_archive_executor.py:305` / `_local_file_digest` | L | query/ORM | `digest_state.update` | ver matriz |
| `backend/app/media_archive_executor.py:477` / `_promote_verified_object` | L | efeito potencial | `_safe_unlink_staging_file` | ver matriz |
| `backend/app/media_archive_executor.py:480` / `_promote_verified_object` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:622` / `_unlink_verified_windows` | L | query/ORM | `digest_state.update` | ver matriz |
| `backend/app/media_archive_executor.py:670` / `_unlink_verified` | L | efeito potencial | `_unlink_verified_windows` | ver matriz |
| `backend/app/media_archive_executor.py:750` / `_unlink_verified` | L | query/ORM | `digest_state.update` | ver matriz |
| `backend/app/media_archive_executor.py:926` / `execute_archive_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_executor.py:1097` / `_verify_restore_manifest` | L | query/ORM | `manifest.get` | ver matriz |
| `backend/app/media_archive_executor.py:1253` / `execute_restore_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_executor.py:153` / `_load_operation_scope` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:682` / `_unlink_verified` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:687` / `_unlink_verified` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_executor.py:717` / `_unlink_verified` | L | efeito potencial | `os.unlink` | ver matriz |
| `backend/app/media_archive_executor.py:932` / `execute_archive_operation` | L | produtor | `MediaArchiveObject` | ver matriz |
| `backend/app/media_archive_executor.py:938` / `execute_archive_operation` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_executor.py:953` / `execute_archive_operation` | L | efeito potencial | `storage.upload_object` | ver matriz |
| `backend/app/media_archive_executor.py:1219` / `execute_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1283` / `execute_restore_operation` | L | efeito potencial | `_download_verified_object` | ver matriz |
| `backend/app/media_archive_executor.py:1390` / `_load_delete_operation_scope` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:157` / `_load_operation_scope` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:492` / `_promote_verified_object` | L | query/ORM | `digest_state.update` | ver matriz |
| `backend/app/media_archive_executor.py:700` / `_unlink_verified` | L | query/ORM | `digest_state.update` | ver matriz |
| `backend/app/media_archive_executor.py:836` / `execute_archive_operation` | L | efeito potencial | `storage.upload_object` | ver matriz |
| `backend/app/media_archive_executor.py:893` / `execute_archive_operation` | L | efeito potencial | `datetime.strptime(previous_manifest['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ').replace` | ver matriz |
| `backend/app/media_archive_executor.py:999` / `execute_archive_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1000` / `execute_archive_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1001` / `execute_archive_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1158` / `_assert_restore_space_is_reserved` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:1247` / `execute_restore_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:1264` / `execute_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1265` / `execute_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1266` / `execute_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1267` / `execute_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_executor.py:1397` / `_load_delete_operation_scope` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:926` / `execute_archive_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:1253` / `execute_restore_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_executor.py:173` / `_object_rows` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:42` / `never_released_closure_folder` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:46` / `never_released_closure_folder` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:91` / `archive_blocker` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:115` / `archive_blocker` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:126` / `archive_blocker` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:137` / `archive_blocker` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:155` / `lock_archive_scope` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:166` / `lock_archive_scope` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:46` / `never_released_closure_folder` | L | efeito potencial | `select(AuditEvent.id).where(AuditEvent.tenant_id == folder.tenant_id, AuditEvent.event.in_(('photo_folder.published', 'photo_folder.released')), or_(AuditEvent.subject == str(folder.id), AuditEvent.subject.like(f'{folder.id}:%'))).limit` | ver matriz |
| `backend/app/media_archive_guards.py:57` / `isolated_closure_cover_folder` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:60` / `isolated_closure_cover_folder` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:80` / `archive_blocker` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:85` / `archive_blocker` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_guards.py:42` / `never_released_closure_folder` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:57` / `isolated_closure_cover_folder` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:46` / `never_released_closure_folder` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:138` / `archive_blocker` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:60` / `isolated_closure_cover_folder` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:85` / `archive_blocker` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:92` / `archive_blocker` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:116` / `archive_blocker` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:127` / `archive_blocker` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:156` / `lock_archive_scope` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_guards.py:167` / `lock_archive_scope` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:119` / `_utc_timestamp` | L | efeito potencial | `parsed.astimezone(timezone.utc).isoformat(timespec='microseconds').replace` | ver matriz |
| `backend/app/media_archive_manifest.py:336` / `_cover_photo` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:362` / `_candidate_sources` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/media_archive_manifest.py:363` / `_candidate_sources` | L | gate | `owned_record` | ver matriz |
| `backend/app/media_archive_manifest.py:364` / `_candidate_sources` | L | gate | `owned_record` | ver matriz |
| `backend/app/media_archive_manifest.py:374` / `_candidate_sources` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:637` / `resolve_archive_target_path` | L | gate | `owned_record` | ver matriz |
| `backend/app/media_archive_manifest.py:638` / `resolve_archive_target_path` | L | gate | `owned_record` | ver matriz |
| `backend/app/media_archive_manifest.py:646` / `resolve_archive_target_path` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:150` / `canonical_manifest_bytes` | L | query/ORM | `seen_ids.add` | ver matriz |
| `backend/app/media_archive_manifest.py:151` / `canonical_manifest_bytes` | L | query/ORM | `seen_sources.add` | ver matriz |
| `backend/app/media_archive_manifest.py:169` / `canonical_manifest_bytes` | L | query/ORM | `seen_remote_ids.add` | ver matriz |
| `backend/app/media_archive_manifest.py:266` / `_measure` | L | efeito potencial | `os.open` | ver matriz |
| `backend/app/media_archive_manifest.py:329` / `_cover_photo` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:394` / `_candidate_sources` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:403` / `_candidate_sources` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_manifest.py:441` / `_candidate_sources` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:450` / `_candidate_sources` | L | query/ORM | `photo_by_id.get` | ver matriz |
| `backend/app/media_archive_manifest.py:500` / `_candidate_sources` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_manifest.py:537` / `_candidate_sources` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/media_archive_manifest.py:566` / `_candidate_sources` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:654` / `resolve_archive_target_path` | L | query/ORM | `allowed_folder_ids.add` | ver matriz |
| `backend/app/media_archive_manifest.py:657` / `_photo` | L | gate | `owned_record` | ver matriz |
| `backend/app/media_archive_manifest.py:685` / `resolve_archive_target_path` | L | gate | `media_storage.media_namespace` | ver matriz |
| `backend/app/media_archive_manifest.py:829` / `snapshot_archive_objects` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_manifest.py:839` / `snapshot_archive_objects` | L | query/ORM | `existing_by_ref.get` | ver matriz |
| `backend/app/media_archive_manifest.py:912` / `build_archive_manifest` | L | efeito potencial | `timestamp.isoformat(timespec='microseconds').replace` | ver matriz |
| `backend/app/media_archive_manifest.py:430` / `_candidate_sources` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_manifest.py:495` / `_candidate_sources` | L | query/ORM | `adjustment_sources.add` | ver matriz |
| `backend/app/media_archive_manifest.py:689` / `resolve_archive_target_path` | L | gate | `owned_record` | ver matriz |
| `backend/app/media_archive_manifest.py:699` / `resolve_archive_target_path` | L | gate | `media_storage.media_namespace` | ver matriz |
| `backend/app/media_archive_manifest.py:849` / `snapshot_archive_objects` | L | produtor | `MediaArchiveObject` | ver matriz |
| `backend/app/media_archive_manifest.py:859` / `snapshot_archive_objects` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_manifest.py:281` / `_measure` | L | query/ORM | `digest.update` | ver matriz |
| `backend/app/media_archive_manifest.py:646` / `resolve_archive_target_path` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:706` / `resolve_archive_target_path` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:715` / `resolve_archive_target_path` | L | gate | `media_storage.media_namespace` | ver matriz |
| `backend/app/media_archive_manifest.py:329` / `_cover_photo` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:394` / `_candidate_sources` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:441` / `_candidate_sources` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:566` / `_candidate_sources` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:730` / `resolve_archive_target_path` | L | gate | `media_storage.media_namespace` | ver matriz |
| `backend/app/media_archive_manifest.py:375` / `_candidate_sources` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:734` / `resolve_archive_target_path` | L | gate | `owned_record` | ver matriz |
| `backend/app/media_archive_manifest.py:739` / `resolve_archive_target_path` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_manifest.py:404` / `_candidate_sources` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:706` / `resolve_archive_target_path` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:754` / `resolve_archive_target_path` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_manifest.py:829` / `snapshot_archive_objects` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:431` / `_candidate_sources` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:515` / `_candidate_sources` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:754` / `resolve_archive_target_path` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:315` / `_latest_folder_state` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:740` / `resolve_archive_target_path` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_manifest.py:337` / `_cover_photo` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_notices.py:87` / `record_notice` | L | query/ORM | `NOTICE_COPY.get` | ver matriz |
| `backend/app/media_archive_notices.py:90` / `record_notice` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_notices.py:97` / `record_notice` | L | produtor | `MediaArchiveNotice` | ver matriz |
| `backend/app/media_archive_notices.py:129` / `record_transfer_notice` | L | query/ORM | `_TRANSFER_NOTICE_TYPES.get` | ver matriz |
| `backend/app/media_archive_notices.py:132` / `record_transfer_notice` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_notices.py:155` / `supersede_window_notices_for_folder` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_notices.py:72` / `_utc` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/media_archive_notices.py:109` / `record_notice` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_notices.py:112` / `record_notice` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_notices.py:90` / `record_notice` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_notices.py:112` / `record_notice` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_notices.py:156` / `supersede_window_notices_for_folder` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:179` / `_latest_cycle_id` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_scheduler.py:195` / `_latest_cycle_for_update` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_scheduler.py:212` / `_latest_archive_operation_for_update` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_scheduler.py:227` / `_new_cycle` | L | produtor | `MediaArchiveCycle` | ver matriz |
| `backend/app/media_archive_scheduler.py:38` / `_utc` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/media_archive_scheduler.py:110` / `_candidate_folder_ids` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_scheduler.py:152` / `_window_notice_candidate_ids` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_scheduler.py:257` / `enqueue_due_archive_window_notices` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_scheduler.py:261` / `enqueue_due_archive_window_notices` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_scheduler.py:291` / `enqueue_due_archive_window_notices` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_scheduler.py:358` / `enqueue_eligible_archive_operations` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_scheduler.py:366` / `enqueue_eligible_archive_operations` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_scheduler.py:403` / `enqueue_eligible_archive_operations` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_scheduler.py:445` / `enqueue_eligible_archive_operations` | L | produtor | `MediaArchiveOperation` | ver matriz |
| `backend/app/media_archive_scheduler.py:458` / `enqueue_eligible_archive_operations` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_scheduler.py:460` / `enqueue_eligible_archive_operations` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_scheduler.py:312` / `enqueue_due_archive_window_notices` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_scheduler.py:419` / `enqueue_eligible_archive_operations` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_scheduler.py:460` / `enqueue_eligible_archive_operations` | L | produtor | `MediaArchiveEvent` | ver matriz |
| `backend/app/media_archive_scheduler.py:291` / `enqueue_due_archive_window_notices` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:404` / `enqueue_eligible_archive_operations` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:115` / `_window_notice_candidate_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:262` / `enqueue_due_archive_window_notices` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:367` / `enqueue_eligible_archive_operations` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:180` / `_latest_cycle_id` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:196` / `_latest_cycle_for_update` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:141` / `_window_notice_candidate_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:44` / `_candidate_folder_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:56` / `_candidate_folder_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:130` / `_window_notice_candidate_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:213` / `_latest_archive_operation_for_update` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:79` / `_candidate_folder_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:153` / `_window_notice_candidate_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_scheduler.py:99` / `_candidate_folder_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:292` / `validate_restore_catalog` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_staging.py:300` / `validate_restore_catalog` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_staging.py:337` / `_assert_manifest_matches_catalog` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_staging.py:381` / `reserve_restore_space` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/media_archive_staging.py:383` / `reserve_restore_space` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_staging.py:389` / `reserve_restore_space` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_staging.py:403` / `reserve_restore_space` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_staging.py:471` / `release_restore_space` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_staging.py:260` / `plan_restore_space` | L | query/ORM | `roots.get` | ver matriz |
| `backend/app/media_archive_staging.py:307` / `validate_restore_catalog` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_staging.py:319` / `_same_instant` | L | efeito potencial | `left.replace` | ver matriz |
| `backend/app/media_archive_staging.py:409` / `reserve_restore_space` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_staging.py:416` / `reserve_restore_space` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_staging.py:419` / `reserve_restore_space` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_staging.py:442` / `reserve_restore_space` | L | query/ORM | `own_by_volume.get` | ver matriz |
| `backend/app/media_archive_staging.py:478` / `release_restore_space` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_staging.py:272` / `plan_restore_space` | L | query/ORM | `required.get` | ver matriz |
| `backend/app/media_archive_staging.py:444` / `reserve_restore_space` | L | produtor | `MediaArchiveSpaceReservation` | ver matriz |
| `backend/app/media_archive_staging.py:451` / `reserve_restore_space` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_staging.py:292` / `validate_restore_catalog` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:300` / `validate_restore_catalog` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:337` / `_assert_manifest_matches_catalog` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:527` / `cleanup_restore_staging` | L | efeito potencial | `entry.unlink` | ver matriz |
| `backend/app/media_archive_staging.py:383` / `reserve_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:389` / `reserve_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:403` / `reserve_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:471` / `release_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:307` / `validate_restore_catalog` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:409` / `reserve_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:416` / `reserve_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:419` / `reserve_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_staging.py:478` / `release_restore_space` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:109` / `begin_archive_copy` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:171` / `begin_archive_cleanup` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:223` / `begin_restore_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:228` / `begin_restore_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:246` / `begin_restore_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:360` / `_append_event` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/media_archive_worker.py:439` / `claim_next_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:496` / `claim_next_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:505` / `claim_next_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:551` / `_locked_claim` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:556` / `_locked_claim` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:574` / `_locked_claim` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:623` / `_deletion_batch_for_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:745` / `mark_remote_object_deleted` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:964` / `complete_delete_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:1021` / `complete_restore_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:1028` / `complete_restore_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:344` / `_utc` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/media_archive_worker.py:360` / `_append_event` | L | produtor | `MediaArchiveEvent` | ver matriz |
| `backend/app/media_archive_worker.py:449` / `claim_next_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:709` / `checkpoint_operation` | L | query/ORM | `operation_details.update` | ver matriz |
| `backend/app/media_archive_worker.py:754` / `mark_remote_object_deleted` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:847` / `complete_delete_operation` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_worker.py:886` / `complete_delete_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:901` / `complete_delete_operation` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_worker.py:930` / `complete_delete_operation` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/media_archive_worker.py:165` / `begin_archive_cleanup` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:166` / `begin_archive_cleanup` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:167` / `begin_archive_cleanup` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:237` / `begin_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:238` / `begin_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:239` / `begin_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:470` / `claim_next_operation` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:590` / `_locked_claim` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/media_archive_worker.py:804` / `complete_archive_operation` | L | query/ORM | `(operation.details or {}).get` | ver matriz |
| `backend/app/media_archive_worker.py:805` / `complete_archive_operation` | L | query/ORM | `(operation.details or {}).get` | ver matriz |
| `backend/app/media_archive_worker.py:806` / `complete_archive_operation` | L | query/ORM | `(operation.details or {}).get` | ver matriz |
| `backend/app/media_archive_worker.py:858` / `complete_delete_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:859` / `complete_delete_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:1012` / `complete_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:1013` / `complete_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:1014` / `complete_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:1015` / `complete_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:109` / `begin_archive_copy` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:171` / `begin_archive_cleanup` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:246` / `begin_restore_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:286` / `begin_restore_operation` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/media_archive_worker.py:591` / `_locked_claim` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media_archive_worker.py:697` / `checkpoint_operation` | L | query/ORM | `(operation.details or {}).get` | ver matriz |
| `backend/app/media_archive_worker.py:827` / `complete_archive_operation` | L | query/ORM | `(operation.details or {}).get` | ver matriz |
| `backend/app/media_archive_worker.py:847` / `complete_delete_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:930` / `complete_delete_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:1091` / `fail_operation` | L | efeito potencial | `error_code.replace` | ver matriz |
| `backend/app/media_archive_worker.py:223` / `begin_restore_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:228` / `begin_restore_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:440` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:497` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:552` / `_locked_claim` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:557` / `_locked_claim` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:575` / `_locked_claim` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:745` / `mark_remote_object_deleted` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:964` / `complete_delete_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:1021` / `complete_restore_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:1028` / `complete_restore_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:450` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:591` / `_locked_claim` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:755` / `mark_remote_object_deleted` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:887` / `complete_delete_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:470` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:624` / `_deletion_batch_for_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:902` / `complete_delete_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/media_archive_worker.py:506` / `claim_next_operation` | L | query/ORM | `select` | ver matriz |
| `backend/app/membership_notifications.py:36` / `enqueue_membership_notification` | N | gate | `require_identity_tenant` | ver matriz |
| `backend/app/membership_notifications.py:39` / `enqueue_membership_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/membership_notifications.py:85` / `process_next_membership_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/membership_notifications.py:140` / `mark_membership_notification_read` | N | gate | `owned_record` | ver matriz |
| `backend/app/membership_notifications.py:103` / `process_next_membership_notification` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/membership_notifications.py:104` / `process_next_membership_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/membership_notifications.py:111` / `process_next_membership_notification` | N | efeito potencial | `sender` | ver matriz |
| `backend/app/membership_notifications.py:53` / `enqueue_membership_notification` | N | produtor | `GalleryMembershipNotificationOutbox` | ver matriz |
| `backend/app/membership_notifications.py:65` / `enqueue_membership_notification` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/membership_notifications.py:69` / `enqueue_membership_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/membership_notifications.py:40` / `enqueue_membership_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/membership_notifications.py:107` / `process_next_membership_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/membership_notifications.py:109` / `process_next_membership_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/membership_notifications.py:70` / `enqueue_membership_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/membership_notifications.py:86` / `process_next_membership_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_api.py:189` / `register_mercadopago_routes` | S | query/ORM | `router.get` | ver matriz |
| `backend/app/mercadopago_api.py:291` / `register_mercadopago_routes` | S | query/ORM | `router.get` | ver matriz |
| `backend/app/mercadopago_api.py:308` / `register_mercadopago_routes` | S | query/ORM | `router.get` | ver matriz |
| `backend/app/mercadopago_api.py:333` / `register_mercadopago_routes` | S | query/ORM | `router.get` | ver matriz |
| `backend/app/mercadopago_api.py:348` / `register_mercadopago_routes` | S | query/ORM | `router.get` | ver matriz |
| `backend/app/mercadopago_api.py:382` / `register_mercadopago_routes` | S | query/ORM | `router.get` | ver matriz |
| `backend/app/mercadopago_api.py:237` / `settings_confirm` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_api.py:266` / `settings_resend` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_api.py:343` / `credit_purchase_history` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/mercadopago_api.py:357` / `active_credit_purchases` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/mercadopago_api.py:272` / `settings_resend` | S | efeito potencial | `resend_security_challenge` | ver matriz |
| `backend/app/mercadopago_api.py:443` / `webhook` | S | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/mercadopago_api.py:443` / `webhook` | S | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/mercadopago_api.py:237` / `settings_confirm` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_api.py:266` / `settings_resend` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:41` / `lock_customer` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:51` / `own_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:108` / `prepare_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:118` / `prepare_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:167` / `prepare_payment` | S | produtor | `MercadoPagoPayment` | ver matriz |
| `backend/app/mercadopago_checkout.py:171` / `prepare_payment` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_checkout.py:363` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:364` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:365` / `apply_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:366` / `apply_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:36` / `utc` | S | efeito potencial | `value.replace` | ver matriz |
| `backend/app/mercadopago_checkout.py:58` / `active_payments` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_checkout.py:69` / `payment_orders` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_checkout.py:190` / `freeze_orders` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_checkout.py:206` / `freeze_orders` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/mercadopago_checkout.py:224` / `freeze_orders` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/mercadopago_checkout.py:241` / `external_state` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:241` / `external_state` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:242` / `external_state` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:242` / `external_state` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:279` / `restore_selection` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_checkout.py:312` / `apply_order` | S | query/ORM | `resource.get('transactions', {}).get` | ver matriz |
| `backend/app/mercadopago_checkout.py:318` / `apply_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:372` / `apply_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:396` / `apply_order` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/mercadopago_checkout.py:401` / `apply_order` | S | query/ORM | `method.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:521` / `submit_payment` | S | query/ORM | `response.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:75` / `payment_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_checkout.py:153` / `prepare_payment` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_checkout.py:198` / `freeze_orders` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:269` / `restore_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:274` / `restore_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:282` / `restore_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:289` / `restore_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_checkout.py:294` / `restore_selection` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_checkout.py:305` / `apply_order` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_checkout.py:407` / `apply_order` | S | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/mercadopago_checkout.py:431` / `reconcile` | S | query/ORM | `provider.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:437` / `reconcile` | S | query/ORM | `result.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:444` / `reconcile` | S | query/ORM | `provider.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:551` / `cancel_payment` | S | query/ORM | `provider.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:108` / `prepare_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:294` / `restore_selection` | S | produtor | `PhotoSelection` | ver matriz |
| `backend/app/mercadopago_checkout.py:312` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:313` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:314` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:321` / `apply_order` | S | query/ORM | `method.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:369` / `apply_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:524` / `submit_payment` | S | query/ORM | `response.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:48` / `own_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:66` / `payment_orders` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:224` / `freeze_orders` | S | query/ORM | `delete` | ver matriz |
| `backend/app/mercadopago_checkout.py:279` / `restore_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:315` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:320` / `apply_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:322` / `apply_order` | S | query/ORM | `method.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:337` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:396` / `apply_order` | S | query/ORM | `delete` | ver matriz |
| `backend/app/mercadopago_checkout.py:41` / `lock_customer` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:118` / `prepare_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:269` / `restore_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:274` / `restore_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:282` / `restore_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:289` / `restore_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:305` / `apply_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:323` / `apply_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:324` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:416` / `apply_order` | S | query/ORM | `db.info.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:441` / `reconcile` | S | query/ORM | `row.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:442` / `reconcile` | S | query/ORM | `candidates[0].get` | ver matriz |
| `backend/app/mercadopago_checkout.py:484` / `submit_payment` | S | query/ORM | `item.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:485` / `submit_payment` | S | query/ORM | `item.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:486` / `submit_payment` | S | query/ORM | `item.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:190` / `freeze_orders` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:372` / `apply_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:75` / `payment_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:153` / `prepare_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:198` / `freeze_orders` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_checkout.py:330` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:330` / `apply_order` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:331` / `apply_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:331` / `apply_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_checkout.py:58` / `active_payments` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:56` / `financial_review_items` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:71` / `_financial_review_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:119` / `_lock_finite_wallet` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:130` / `_resolve_owner_account` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:147` / `_resolve_owner_account` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:148` / `_resolve_owner_account` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:170` / `_record_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:176` / `_record_event` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:197` / `prepare_credit_purchase` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:212` / `prepare_credit_purchase` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:221` / `prepare_credit_purchase` | S | produtor | `MercadoPagoCreditPurchase` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:239` / `prepare_credit_purchase` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:258` / `owned_credit_purchase` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:265` / `list_credit_purchases` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:274` / `active_credit_purchases` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:434` / `_valid_order_resource` | S | query/ORM | `resource.get('transactions', {}).get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:441` / `_valid_order_resource` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:459` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:472` / `_ensure_purchase_ledger` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:478` / `_ensure_purchase_ledger` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:694` / `resolve_credit_purchase_review` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:42` / `tenant_has_financial_hold` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:133` / `_resolve_owner_account` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:176` / `_record_event` | S | produtor | `MercadoPagoCreditPurchaseEvent` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:414` / `submit_credit_purchase` | S | query/ORM | `response.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:483` / `_ensure_purchase_ledger` | S | produtor | `PhotographerCreditEntry` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:493` / `_ensure_purchase_ledger` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:556` / `apply_credit_order` | S | query/ORM | `{'partially_refunded': 1, 'refunded': 2, 'charged_back': 3}.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:565` / `apply_credit_order` | S | query/ORM | `transaction.get('payment_method', {}).get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:648` / `process_next_mercadopago_credit_purchase` | S | gate | `domain_session` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:649` / `process_next_mercadopago_credit_purchase` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:665` / `process_next_mercadopago_credit_purchase` | S | gate | `domain_session` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:666` / `process_next_mercadopago_credit_purchase` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:49` / `financial_review_count` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:103` / `financial_review_queue` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:434` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:435` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:437` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:444` / `_valid_order_resource` | S | query/ORM | `payment_method.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:601` / `_reconcile_locked` | S | query/ORM | `provider.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:608` / `_reconcile_locked` | S | query/ORM | `result.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:614` / `_reconcile_locked` | S | query/ORM | `provider.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:148` / `_resolve_owner_account` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:170` / `_record_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:197` / `prepare_credit_purchase` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:212` / `prepare_credit_purchase` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:416` / `submit_credit_purchase` | S | query/ORM | `response.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:438` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:443` / `_valid_order_resource` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:445` / `_valid_order_resource` | S | query/ORM | `payment_method.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:466` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:565` / `apply_credit_order` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:254` / `owned_credit_purchase` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:446` / `_valid_order_resource` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:447` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:49` / `financial_review_count` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:71` / `_financial_review_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:119` / `_lock_finite_wallet` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:274` / `active_credit_purchases` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:374` / `submit_credit_purchase` | S | query/ORM | `item.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:375` / `submit_credit_purchase` | S | query/ORM | `item.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:376` / `submit_credit_purchase` | S | query/ORM | `item.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:472` / `_ensure_purchase_ledger` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:478` / `_ensure_purchase_ledger` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:611` / `_reconcile_locked` | S | query/ORM | `row.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:612` / `_reconcile_locked` | S | query/ORM | `candidates[0].get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:694` / `resolve_credit_purchase_review` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:42` / `tenant_has_financial_hold` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:453` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:454` / `_valid_order_resource` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:455` / `_valid_order_resource` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:456` / `_valid_order_resource` | S | query/ORM | `transaction.get` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:666` / `process_next_mercadopago_credit_purchase` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:56` / `financial_review_items` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:265` / `list_credit_purchases` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:134` / `_resolve_owner_account` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:649` / `process_next_mercadopago_credit_purchase` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:104` / `financial_review_queue` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_credit_purchases.py:657` / `process_next_mercadopago_credit_purchase` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_projection.py:21` / `financial_status` | S | query/ORM, efeito potencial | `{'prepared': 'awaiting_payment', 'sending': 'verifying', 'initiated': 'awaiting_payment', 'pending': 'awaiting_payment', 'processing': 'processing', 'verification_required': 'verifying', 'abandoned': 'canceled'}.get` | ver matriz |
| `backend/app/mercadopago_projection.py:29` / `financial_fields` | S | query/ORM | `payments.get` | ver matriz |
| `backend/app/mercadopago_projection.py:51` / `purchase_groups` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/mercadopago_projection.py:12` / `mercadopago_for_orders` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/mercadopago_projection.py:12` / `mercadopago_for_orders` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_provider.py:61` / `_call` | S | query/ORM | `result.get` | ver matriz |
| `backend/app/mercadopago_provider.py:65` / `_call` | S | query/ORM | `result.get` | ver matriz |
| `backend/app/mercadopago_provider.py:28` / `request` | S | produtor | `httpx.Client` | ver matriz |
| `backend/app/mercadopago_provider.py:29` / `request` | S | query/ORM | `kwargs.get` | ver matriz |
| `backend/app/mercadopago_provider.py:30` / `request` | S | query/ORM | `kwargs.get` | ver matriz |
| `backend/app/mercadopago_provider.py:30` / `request` | S | query/ORM | `kwargs.get` | ver matriz |
| `backend/app/mercadopago_settings.py:18` / `preferences` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/mercadopago_settings.py:19` / `preferences` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_settings.py:26` / `account_for` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_settings.py:90` / `credential_provider` | K | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/mercadopago_settings.py:125` / `prepare_proposal` | K | produtor | `MercadoPagoAccount` | ver matriz |
| `backend/app/mercadopago_settings.py:146` / `apply_proposal` | K | produtor | `PaymentPreferences` | ver matriz |
| `backend/app/mercadopago_settings.py:147` / `apply_proposal` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_settings.py:150` / `apply_proposal` | K | produtor | `MercadoPagoAccount` | ver matriz |
| `backend/app/mercadopago_settings.py:152` / `apply_proposal` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_settings.py:52` / `test_customer_allowed` | K | query/ORM | `allowed.add` | ver matriz |
| `backend/app/mercadopago_settings.py:112` / `prepare_proposal` | K | query/ORM | `identity.get` | ver matriz |
| `backend/app/mercadopago_settings.py:120` / `prepare_proposal` | K | efeito potencial | `cipher.encrypt(token, tenant_id=tenant_id, credential_id=account_id).payload` | ver matriz |
| `backend/app/mercadopago_settings.py:122` / `prepare_proposal` | K | efeito potencial | `cipher.encrypt(signature, tenant_id=tenant_id, credential_id=account_id).payload` | ver matriz |
| `backend/app/mercadopago_settings.py:113` / `prepare_proposal` | K | query/ORM | `identity.get` | ver matriz |
| `backend/app/mercadopago_settings.py:119` / `prepare_proposal` | K | query/ORM | `identity.get` | ver matriz |
| `backend/app/mercadopago_settings.py:120` / `prepare_proposal` | K | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/mercadopago_settings.py:122` / `prepare_proposal` | K | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/mercadopago_settings.py:19` / `preferences` | K | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_settings.py:26` / `account_for` | K | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:33` / `receive_notification` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:36` / `receive_notification` | S | query/ORM | `query.get` | ver matriz |
| `backend/app/mercadopago_webhook.py:73` / `receive_notification` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:54` / `receive_notification` | S | efeito potencial | `IntegrationCipher().decrypt` | ver matriz |
| `backend/app/mercadopago_webhook.py:94` / `process_next_mercadopago_event` | S | gate | `domain_session` | ver matriz |
| `backend/app/mercadopago_webhook.py:95` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:109` / `process_next_mercadopago_event` | S | gate | `domain_session` | ver matriz |
| `backend/app/mercadopago_webhook.py:111` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:117` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:176` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:187` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:209` / `reconcile_next_mercadopago_payment` | S | gate | `domain_session` | ver matriz |
| `backend/app/mercadopago_webhook.py:210` / `reconcile_next_mercadopago_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:217` / `reconcile_next_mercadopago_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:38` / `receive_notification` | S | query/ORM | `body.get` | ver matriz |
| `backend/app/mercadopago_webhook.py:40` / `receive_notification` | S | query/ORM | `body['data'].get` | ver matriz |
| `backend/app/mercadopago_webhook.py:137` / `process_next_mercadopago_event` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_webhook.py:33` / `receive_notification` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:39` / `receive_notification` | S | query/ORM | `body.get` | ver matriz |
| `backend/app/mercadopago_webhook.py:73` / `receive_notification` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:79` / `receive_notification` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/mercadopago_webhook.py:125` / `process_next_mercadopago_event` | S | query/ORM | `credential_provider(event_account).get` | ver matriz |
| `backend/app/mercadopago_webhook.py:127` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:157` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:79` / `receive_notification` | S | produtor | `MercadoPagoWebhook` | ver matriz |
| `backend/app/mercadopago_webhook.py:84` / `receive_notification` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:117` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:126` / `process_next_mercadopago_event` | S | query/ORM | `resource.get` | ver matriz |
| `backend/app/mercadopago_webhook.py:145` / `process_next_mercadopago_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/mercadopago_webhook.py:176` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:217` / `reconcile_next_mercadopago_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:111` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:118` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:187` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:84` / `receive_notification` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:127` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:157` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:210` / `reconcile_next_mercadopago_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:145` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:95` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:211` / `reconcile_next_mercadopago_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/mercadopago_webhook.py:96` / `process_next_mercadopago_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/messaging.py:69` / `send_otp` | N | efeito potencial | `self.send_transactional` | ver matriz |
| `backend/app/messaging.py:209` / `send_transactional` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:210` / `send_transactional` | N | query/ORM | `key.get` | ver matriz |
| `backend/app/messaging.py:210` / `send_transactional` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:210` / `send_transactional` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:229` / `connection_status` | N | query/ORM | `state_body.get` | ver matriz |
| `backend/app/messaging.py:310` / `start_pairing` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:312` / `start_pairing` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:312` / `start_pairing` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:313` / `start_pairing` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:313` / `start_pairing` | N | query/ORM | `_first_mapping(body.get('qrcode')).get` | ver matriz |
| `backend/app/messaging.py:209` / `send_transactional` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:212` / `send_transactional` | N | query/ORM | `key.get` | ver matriz |
| `backend/app/messaging.py:212` / `send_transactional` | N | query/ORM | `key.get` | ver matriz |
| `backend/app/messaging.py:212` / `send_transactional` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:268` / `ensure_instance` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:311` / `start_pairing` | N | query/ORM | `nested.get` | ver matriz |
| `backend/app/messaging.py:311` / `start_pairing` | N | query/ORM | `nested.get` | ver matriz |
| `backend/app/messaging.py:311` / `start_pairing` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:240` / `connection_status` | N | query/ORM | `instance_body.get` | ver matriz |
| `backend/app/messaging.py:241` / `connection_status` | N | query/ORM | `instance_body.get` | ver matriz |
| `backend/app/messaging.py:242` / `connection_status` | N | query/ORM | `_first_mapping(instance_body.get('instance')).get` | ver matriz |
| `backend/app/messaging.py:220` / `send_transactional` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:230` / `connection_status` | N | query/ORM | `nested.get` | ver matriz |
| `backend/app/messaging.py:230` / `connection_status` | N | query/ORM | `state_body.get` | ver matriz |
| `backend/app/messaging.py:313` / `start_pairing` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/messaging.py:242` / `connection_status` | N | query/ORM | `instance_body.get` | ver matriz |
| `backend/app/messaging.py:271` / `ensure_instance` | N | query/ORM | `nested.get` | ver matriz |
| `backend/app/messaging.py:271` / `ensure_instance` | N | query/ORM | `body.get` | ver matriz |
| `backend/app/notification_delivery.py:69` / `mirror_payment_projection` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:80` / `recipient_allowed` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_delivery.py:343` / `retry_payment_projection` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_delivery.py:344` / `retry_payment_projection` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:347` / `retry_payment_projection` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:56` / `utc` | N | efeito potencial | `value.replace` | ver matriz |
| `backend/app/notification_delivery.py:85` / `recipient_allowed` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:98` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:128` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:132` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:149` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:215` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:225` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:243` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:327` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:352` / `retry_payment_projection` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_delivery.py:99` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:105` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:106` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:169` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:177` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:187` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:200` / `process_next_notification` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_delivery.py:211` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:235` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:244` / `process_next_notification` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:258` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:69` / `mirror_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:93` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:153` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:183` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:238` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:344` / `retry_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:89` / `recipient_allowed` | N | gate | `require_admin_tenant` | ver matriz |
| `backend/app/notification_delivery.py:272` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:278` / `process_next_notification` | N | efeito potencial | `push_sender or send_push` | ver matriz |
| `backend/app/notification_delivery.py:283` / `process_next_notification` | N | gate | `provider_for` | ver matriz |
| `backend/app/notification_delivery.py:287` / `process_next_notification` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:299` / `process_next_notification` | N | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/notification_delivery.py:318` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:187` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:273` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:278` / `process_next_notification` | N | efeito potencial | `decrypt_subscription` | ver matriz |
| `backend/app/notification_delivery.py:294` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:133` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:225` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:327` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:352` / `retry_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:106` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:238` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:294` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:318` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:200` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:215` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:47` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:48` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:67` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:100` / `record_restricted_folder_ready` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:122` / `record_restricted_folder_ready` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_events.py:152` / `record_payment_event` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_events.py:155` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:176` / `record_payment_event` | N | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/notification_events.py:36` / `legacy_owned_photographer_phone` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_events.py:59` / `record_gallery_milestone` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_events.py:123` / `record_restricted_folder_ready` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:138` / `record_restricted_folder_ready` | N | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/notification_events.py:156` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:157` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:163` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:190` / `record_payment_event` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_events.py:71` / `record_gallery_milestone` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_events.py:73` / `record_gallery_milestone` | N | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/notification_events.py:131` / `record_restricted_folder_ready` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_events.py:158` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:171` / `record_payment_event` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_events.py:193` / `record_payment_event` | N | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/notification_events.py:195` / `record_payment_event` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_events.py:71` / `record_gallery_milestone` | N | produtor | `NotificationMilestone` | ver matriz |
| `backend/app/notification_events.py:87` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:195` / `record_payment_event` | N | produtor | `PaymentNotificationOutbox` | ver matriz |
| `backend/app/notification_events.py:59` / `record_gallery_milestone` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:190` / `record_payment_event` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:78` / `record_gallery_milestone` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_events.py:131` / `record_restricted_folder_ready` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:103` / `record_restricted_folder_ready` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:171` / `record_payment_event` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:78` / `record_gallery_milestone` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:166` / `setting_for` | K | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_settings.py:171` / `setting_for` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:190` / `payment_template_bodies` | K | gate | `require_identity_tenant` | ver matriz |
| `backend/app/notification_settings.py:191` / `payment_template_bodies` | K | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_settings.py:204` / `payment_template_migration_sources` | K | gate | `require_identity_tenant` | ver matriz |
| `backend/app/notification_settings.py:258` / `save_setting` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:331` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:51` / `validate_text` | K | query/ORM | `allowed.update` | ver matriz |
| `backend/app/notification_settings.py:153` / `_require_event_tenant` | K | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_settings.py:158` / `_require_event_tenant` | K | gate | `require_identity_tenant` | ver matriz |
| `backend/app/notification_settings.py:174` / `setting_for` | K | query/ORM | `DEFAULT_PAYMENT_TEMPLATES.get` | ver matriz |
| `backend/app/notification_settings.py:216` / `payment_template_migration_sources` | K | query/ORM | `configured.get` | ver matriz |
| `backend/app/notification_settings.py:349` / `enqueue_event` | K | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_settings.py:379` / `enqueue_event` | K | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_settings.py:398` / `enqueue_event` | K | query/ORM | `whatsapp_values.get` | ver matriz |
| `backend/app/notification_settings.py:401` / `enqueue_event` | K | query/ORM | `whatsapp_values.get` | ver matriz |
| `backend/app/notification_settings.py:92` / `render_whatsapp_text` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:111` / `render_whatsapp_text` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:177` / `setting_for` | K | produtor | `NotificationSetting` | ver matriz |
| `backend/app/notification_settings.py:179` / `setting_for` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:182` / `setting_for` | K | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_settings.py:208` / `payment_template_migration_sources` | K | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_settings.py:264` / `save_setting` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:265` / `save_setting` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:266` / `save_setting` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:271` / `save_setting` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:287` / `save_setting` | K | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_settings.py:323` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:328` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:350` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:356` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:380` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:406` / `enqueue_event` | K | produtor | `NotificationEvent` | ver matriz |
| `backend/app/notification_settings.py:416` / `enqueue_event` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:455` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:65` / `render_text` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:87` / `render_whatsapp_text` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:155` / `_require_event_tenant` | K | query/ORM | `db.info.get` | ver matriz |
| `backend/app/notification_settings.py:171` / `setting_for` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:296` / `save_setting` | K | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_settings.py:316` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:331` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:193` / `payment_template_bodies` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:429` / `enqueue_event` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:436` / `enqueue_event` | K | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_settings.py:191` / `payment_template_bodies` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:208` / `payment_template_migration_sources` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:258` / `save_setting` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:323` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:328` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:429` / `enqueue_event` | K | produtor | `NotificationDelivery` | ver matriz |
| `backend/app/notification_settings.py:442` / `enqueue_event` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:455` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:316` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:442` / `enqueue_event` | K | produtor | `NotificationDelivery` | ver matriz |
| `backend/app/notification_settings.py:287` / `save_setting` | K | query/ORM | `update` | ver matriz |
| `backend/app/notification_settings.py:350` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:356` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:380` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:436` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:296` / `save_setting` | K | query/ORM | `update` | ver matriz |
| `backend/app/notification_settings.py:289` / `save_setting` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:298` / `save_setting` | K | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:27` / `suspend_delivery_access` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/order_delivery.py:87` / `lock_delivery_order` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/order_delivery.py:88` / `lock_delivery_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:92` / `lock_delivery_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:93` / `lock_delivery_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:106` / `record_delivery_notice` | S | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/order_delivery.py:153` / `resend_delivery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:162` / `delivery_notice_allowed` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:173` / `delivery_notice_allowed` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/order_delivery.py:182` / `delivery_notice_allowed` | S | query/ORM, efeito potencial | `{'order-delivery': 3, 'order-delivery-resend': 4}.get` | ver matriz |
| `backend/app/order_delivery.py:114` / `record_delivery_notice` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/order_delivery.py:125` / `set_delivery` | S | gate | `require_admin_tenant` | ver matriz |
| `backend/app/order_delivery.py:145` / `resend_delivery` | S | gate | `require_admin_tenant` | ver matriz |
| `backend/app/order_delivery.py:88` / `lock_delivery_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:153` / `resend_delivery` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:27` / `suspend_delivery_access` | S | query/ORM | `update` | ver matriz |
| `backend/app/order_delivery.py:92` / `lock_delivery_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:114` / `record_delivery_notice` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:162` / `delivery_notice_allowed` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:29` / `suspend_delivery_access` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:93` / `lock_delivery_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_visibility.py:16` / `visible_sale_order_condition` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_visibility.py:18` / `visible_sale_order_condition` | S | query/ORM | `select` | ver matriz |
| `backend/app/ownership_schema.py:94` / `apply_ownership_constraints` | X | query/ORM | `metadata.info.get` | ver matriz |
| `backend/app/ownership_schema.py:113` / `apply_ownership_constraints` | X | query/ORM | `UNSCOPED_CONTEXTUAL_UNIQUES.get` | ver matriz |
| `backend/app/parent_registration.py:21` / `link_client_to_parent` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/parent_registration.py:22` / `link_client_to_parent` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/parent_registration.py:25` / `link_client_to_parent` | G | gate | `require_client_owner` | ver matriz |
| `backend/app/parent_registration.py:27` / `link_client_to_parent` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/parent_registration.py:40` / `link_client_to_parent` | G | produtor | `ParentGalleryRegistration` | ver matriz |
| `backend/app/parent_registration.py:46` / `link_client_to_parent` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/parent_registration.py:49` / `link_client_to_parent` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/parent_registration.py:28` / `link_client_to_parent` | G | query/ORM | `select` | ver matriz |
| `backend/app/parent_registration.py:50` / `link_client_to_parent` | G | query/ORM | `select` | ver matriz |
| `backend/app/payment_availability.py:26` / `lock_payment_account` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/payment_availability.py:33` / `payment_methods` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/payment_availability.py:25` / `lock_payment_account` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/payment_availability.py:29` / `lock_payment_account` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/payment_availability.py:60` / `has_published_paid_gallery` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/payment_availability.py:60` / `has_published_paid_gallery` | K | query/ORM | `select` | ver matriz |
| `backend/app/payment_availability.py:26` / `lock_payment_account` | K | query/ORM | `select` | ver matriz |
| `backend/app/payment_availability.py:65` / `has_published_paid_gallery` | K | query/ORM | `select` | ver matriz |
| `backend/app/payment_export.py:33` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_export.py:27` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_export.py:28` / `payment_orders_csv` | S | query/ORM | `mp.get` | ver matriz |
| `backend/app/payment_export.py:40` / `payment_orders_csv` | S | query/ORM | `mp.get` | ver matriz |
| `backend/app/payment_export.py:36` / `payment_orders_csv` | S | efeito potencial | `instant.replace` | ver matriz |
| `backend/app/payment_export.py:50` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_export.py:50` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_export.py:51` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_export.py:51` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_export.py:48` / `payment_orders_csv` | S | query/ORM | `mp.get` | ver matriz |
| `backend/app/payment_export.py:48` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_export.py:49` / `payment_orders_csv` | S | query/ORM | `((order.get('communication') or {}).get('payment_group') or {}).get` | ver matriz |
| `backend/app/payment_export.py:52` / `payment_orders_csv` | S | query/ORM | `mp.get` | ver matriz |
| `backend/app/payment_export.py:52` / `payment_orders_csv` | S | query/ORM | `mp.get` | ver matriz |
| `backend/app/payment_export.py:53` / `payment_orders_csv` | S | query/ORM | `mp.get` | ver matriz |
| `backend/app/payment_export.py:53` / `payment_orders_csv` | S | query/ORM | `mp.get` | ver matriz |
| `backend/app/payment_export.py:49` / `payment_orders_csv` | S | query/ORM | `(order.get('communication') or {}).get` | ver matriz |
| `backend/app/payment_export.py:49` / `payment_orders_csv` | S | query/ORM | `order.get` | ver matriz |
| `backend/app/payment_templates.py:27` / `validate_template` | K | efeito potencial | `body.replace('\r\n', '\n').replace` | ver matriz |
| `backend/app/payment_templates.py:27` / `validate_template` | K | efeito potencial | `body.replace` | ver matriz |
| `backend/app/photographer_access_recovery.py:359` / `<módulo>` | A | query/ORM | `owner_router.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:103` / `_target` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:112` / `_target` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:118` / `_payload` | A | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/photographer_access_recovery.py:122` / `_save_payload` | A | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/photographer_access_recovery.py:133` / `cleanup_expired_recoveries` | A | query/ORM | `(db.get_bind().get_execution_options().get('schema_translate_map') or {}).get` | ver matriz |
| `backend/app/photographer_access_recovery.py:169` / `start_recovery` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:182` / `start_recovery` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:197` / `start_recovery` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_access_recovery.py:206` / `start_recovery` | A | produtor | `PhotographerAccessRecovery` | ver matriz |
| `backend/app/photographer_access_recovery.py:215` / `start_recovery` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_access_recovery.py:218` / `start_recovery` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/photographer_access_recovery.py:228` / `verify_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:233` / `verify_recovery` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:234` / `verify_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:260` / `commit_recovery` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:261` / `commit_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:267` / `commit_recovery` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:295` / `commit_recovery` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_access_recovery.py:299` / `commit_recovery` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_access_recovery.py:304` / `commit_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:321` / `validate_recovery_email` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_access_recovery.py:346` / `completed_closure_proof` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_access_recovery.py:361` / `lookup` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_access_recovery.py:377` / `start` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_access_recovery.py:399` / `commit` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_access_recovery.py:423` / `confirm` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_access_recovery.py:108` / `_target` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:142` / `cleanup_expired_recoveries` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_access_recovery.py:202` / `start_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:136` / `cleanup_expired_recoveries` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:159` / `_collision` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:161` / `_collision` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_access_recovery.py:366` / `lookup` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_access_recovery.py:133` / `cleanup_expired_recoveries` | A | query/ORM | `db.get_bind().get_execution_options().get` | ver matriz |
| `backend/app/photographer_access_recovery.py:150` / `utc` | A | efeito potencial | `value.replace` | ver matriz |
| `backend/app/photographer_access_recovery.py:228` / `verify_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:295` / `commit_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:299` / `commit_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:304` / `commit_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:333` / `completed_closure_proof` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:197` / `start_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:108` / `_target` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:159` / `_collision` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:161` / `_collision` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:234` / `verify_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:261` / `commit_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:202` / `start_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_access_recovery.py:366` / `lookup` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_cpf.py:90` / `_fingerprint` | A | query/ORM | `keys.get` | ver matriz |
| `backend/app/photographer_cpf.py:132` / `cpf_matches_tenant` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_cpf.py:112` / `active_cpf_fingerprint` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_cpf.py:113` / `active_cpf_fingerprint` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_cpf.py:125` / `active_cpf_fingerprint` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_cpf.py:112` / `active_cpf_fingerprint` | A | query/ORM | `text` | ver matriz |
| `backend/app/photographer_cpf.py:120` / `active_cpf_fingerprint` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_cpf.py:132` / `cpf_matches_tenant` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_cpf.py:114` / `active_cpf_fingerprint` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:77` / `wallet_snapshot` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_credits.py:140` / `list_entries` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:153` / `list_packages` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:161` / `list_active_packages` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:435` / `create_package` | S | produtor | `PhotographerCreditPackage` | ver matriz |
| `backend/app/photographer_credits.py:445` / `create_package` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:465` / `update_package` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:501` / `grant_credits` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:507` / `grant_credits` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:521` / `grant_credits` | S | produtor | `PhotographerCreditEntry` | ver matriz |
| `backend/app/photographer_credits.py:530` / `grant_credits` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:557` / `revoke_grant` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:573` / `revoke_grant` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:583` / `revoke_grant` | S | produtor | `PhotographerCreditEntry` | ver matriz |
| `backend/app/photographer_credits.py:593` / `revoke_grant` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:595` / `revoke_grant` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:627` / `reserve_photo_credit` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:670` / `reserve_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:679` / `reserve_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:701` / `record_upload_attempt` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:739` / `consume_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:747` / `consume_photo_credit` | S | produtor | `PhotographerCreditEntry` | ver matriz |
| `backend/app/photographer_credits.py:758` / `consume_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:760` / `consume_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:772` / `consume_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:825` / `release_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:878` / `_claim_stale_photo_credit_operation` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:1000` / `_lock_wallet` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:1016` / `_lock_operation` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:1051` / `_oldest_available_source` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:1091` / `_require_operation_reservation` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:1102` / `_require_allocation_event` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:85` / `wallet_snapshot` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:89` / `wallet_snapshot` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:95` / `wallet_snapshot` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:105` / `wallet_snapshot` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:258` / `list_credit_tenants` | S | query/ORM | `pending_totals.get` | ver matriz |
| `backend/app/photographer_credits.py:259` / `list_credit_tenants` | S | query/ORM | `archive_pending_totals.get` | ver matriz |
| `backend/app/photographer_credits.py:365` / `credit_tenant_detail` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_credits.py:368` / `credit_tenant_detail` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:403` / `credit_tenant_detail` | S | query/ORM | `allocation_totals.get` | ver matriz |
| `backend/app/photographer_credits.py:405` / `credit_tenant_detail` | S | query/ORM | `totals.get` | ver matriz |
| `backend/app/photographer_credits.py:595` / `revoke_grant` | S | produtor | `PhotographerCreditAllocationEvent` | ver matriz |
| `backend/app/photographer_credits.py:654` / `reserve_photo_credit` | S | produtor | `PhotoCreditOperation` | ver matriz |
| `backend/app/photographer_credits.py:663` / `reserve_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:670` / `reserve_photo_credit` | S | produtor | `PhotographerCreditAllocationEvent` | ver matriz |
| `backend/app/photographer_credits.py:679` / `reserve_photo_credit` | S | produtor | `PhotoCreditOperationEvent` | ver matriz |
| `backend/app/photographer_credits.py:701` / `record_upload_attempt` | S | produtor | `PhotoCreditOperationEvent` | ver matriz |
| `backend/app/photographer_credits.py:727` / `consume_photo_credit` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:739` / `consume_photo_credit` | S | produtor | `PhotoCreditOperationEvent` | ver matriz |
| `backend/app/photographer_credits.py:760` / `consume_photo_credit` | S | produtor | `PhotographerCreditAllocationEvent` | ver matriz |
| `backend/app/photographer_credits.py:772` / `consume_photo_credit` | S | produtor | `PhotoCreditOperationEvent` | ver matriz |
| `backend/app/photographer_credits.py:825` / `release_photo_credit` | S | produtor | `PhotoCreditOperationEvent` | ver matriz |
| `backend/app/photographer_credits.py:964` / `reconcile_next_stale_photo_credit_operation` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:1026` / `_allocation_events` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:1034` / `_source_available` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:1061` / `_active_operation_sources` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_credits.py:47` / `source_fingerprint_state` | S | efeito potencial | `path.open` | ver matriz |
| `backend/app/photographer_credits.py:111` / `wallet_snapshot` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:115` / `wallet_snapshot` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_credits.py:174` / `list_credit_tenants` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:246` / `list_credit_tenants` | S | efeito potencial | `db.execute(select(PhotographerCreditEntry.tenant_id, func.sum(-PhotographerCreditEntry.delta)).where(PhotographerCreditEntry.entry_type == 'upload_consumption', PhotographerCreditEntry.created_at >= as_of - timedelta(days=30)).group_by(PhotographerCreditEntry.tenant_id)).all` | ver matriz |
| `backend/app/photographer_credits.py:267` / `list_credit_tenants` | S | query/ORM | `recent_consumption.get` | ver matriz |
| `backend/app/photographer_credits.py:346` / `browse_credit_tenants` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:404` / `credit_tenant_detail` | S | query/ORM | `totals.get` | ver matriz |
| `backend/app/photographer_credits.py:404` / `credit_tenant_detail` | S | query/ORM | `totals.get` | ver matriz |
| `backend/app/photographer_credits.py:406` / `credit_tenant_detail` | S | query/ORM | `totals.get` | ver matriz |
| `backend/app/photographer_credits.py:406` / `credit_tenant_detail` | S | query/ORM | `totals.get` | ver matriz |
| `backend/app/photographer_credits.py:812` / `release_photo_credit` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_credits.py:906` / `reconcile_next_stale_photo_credit_operation` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:931` / `reconcile_next_stale_photo_credit_operation` | S | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_credits.py:964` / `reconcile_next_stale_photo_credit_operation` | S | produtor | `PhotoCreditOperationEvent` | ver matriz |
| `backend/app/photographer_credits.py:49` / `source_fingerprint_state` | S | query/ORM | `digest.update` | ver matriz |
| `backend/app/photographer_credits.py:153` / `list_packages` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:260` / `list_credit_tenants` | S | query/ORM | `ledger_balances.get` | ver matriz |
| `backend/app/photographer_credits.py:266` / `list_credit_tenants` | S | query/ORM | `archive_pending_counts.get` | ver matriz |
| `backend/app/photographer_credits.py:375` / `credit_tenant_detail` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:387` / `credit_tenant_detail` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:399` / `credit_tenant_detail` | S | query/ORM | `totals.get` | ver matriz |
| `backend/app/photographer_credits.py:507` / `grant_credits` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:557` / `revoke_grant` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:812` / `release_photo_credit` | S | produtor | `PhotographerCreditAllocationEvent` | ver matriz |
| `backend/app/photographer_credits.py:1091` / `_require_operation_reservation` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:1102` / `_require_allocation_event` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:85` / `wallet_snapshot` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:89` / `wallet_snapshot` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:95` / `wallet_snapshot` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:105` / `wallet_snapshot` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:206` / `list_credit_tenants` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:213` / `list_credit_tenants` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:223` / `list_credit_tenants` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:234` / `list_credit_tenants` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:246` / `list_credit_tenants` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_credits.py:310` / `browse_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:727` / `consume_photo_credit` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:111` / `wallet_snapshot` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:115` / `wallet_snapshot` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:161` / `list_active_packages` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:246` / `list_credit_tenants` | S | efeito potencial | `select(PhotographerCreditEntry.tenant_id, func.sum(-PhotographerCreditEntry.delta)).where(PhotographerCreditEntry.entry_type == 'upload_consumption', PhotographerCreditEntry.created_at >= as_of - timedelta(days=30)).group_by` | ver matriz |
| `backend/app/photographer_credits.py:465` / `update_package` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:501` / `grant_credits` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:573` / `revoke_grant` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:627` / `reserve_photo_credit` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:1000` / `_lock_wallet` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:1016` / `_lock_operation` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:368` / `credit_tenant_detail` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:1026` / `_allocation_events` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:1034` / `_source_available` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:1061` / `_active_operation_sources` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:140` / `list_entries` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:206` / `list_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:322` / `browse_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:879` / `_claim_stale_photo_credit_operation` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:1051` / `_oldest_available_source` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:302` / `browse_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:375` / `credit_tenant_detail` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:387` / `credit_tenant_detail` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:213` / `list_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:223` / `list_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:234` / `list_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:246` / `list_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:175` / `list_credit_tenants` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_credits.py:907` / `reconcile_next_stale_photo_credit_operation` | S | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:244` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_onboarding.py:262` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_onboarding.py:285` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_onboarding.py:302` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_onboarding.py:454` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_onboarding.py:466` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_onboarding.py:90` / `_context` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_onboarding.py:91` / `_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:96` / `_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:131` / `onboarding_status` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:142` / `onboarding_status` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_onboarding.py:184` / `_signup_identity` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:195` / `require_credit_purchase_ready` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_onboarding.py:232` / `require_upload_ready` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_onboarding.py:254` / `_address_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:256` / `_address_context` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_onboarding.py:305` / `checkout_identity` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:331` / `save_profile` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:367` / `save_profile` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_onboarding.py:385` / `accept_local_test_terms` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:391` / `accept_local_test_terms` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:399` / `accept_local_test_terms` | A | produtor | `PhotographerTermsAcceptance` | ver matriz |
| `backend/app/photographer_onboarding.py:405` / `accept_local_test_terms` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_onboarding.py:416` / `accept_published_terms` | A | efeito potencial | `latest_published` | ver matriz |
| `backend/app/photographer_onboarding.py:419` / `accept_published_terms` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:425` / `accept_published_terms` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:441` / `accept_published_terms` | A | produtor | `PhotographerTermsAcceptance` | ver matriz |
| `backend/app/photographer_onboarding.py:448` / `accept_published_terms` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_onboarding.py:457` / `own_term_acceptances` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_onboarding.py:469` / `download_own_term_acceptance` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:114` / `_terms_version` | A | efeito potencial | `latest_published` | ver matriz |
| `backend/app/photographer_onboarding.py:136` / `onboarding_status` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:312` / `checkout_identity` | A | efeito potencial | `decrypt_private_field` | ver matriz |
| `backend/app/photographer_onboarding.py:346` / `save_profile` | A | efeito potencial | `encrypt_private_field` | ver matriz |
| `backend/app/photographer_onboarding.py:357` / `save_profile` | A | efeito potencial | `encrypt_private_document` | ver matriz |
| `backend/app/photographer_onboarding.py:362` / `save_profile` | A | produtor | `PhotographerBusinessProfile` | ver matriz |
| `backend/app/photographer_onboarding.py:218` / `require_upload_ready` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_onboarding.py:314` / `checkout_identity` | A | efeito potencial | `decrypt_private_document` | ver matriz |
| `backend/app/photographer_onboarding.py:91` / `_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:96` / `_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:131` / `onboarding_status` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:147` / `onboarding_status` | A | query/ORM | `credit_snapshot.get` | ver matriz |
| `backend/app/photographer_onboarding.py:184` / `_signup_identity` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:254` / `_address_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:305` / `checkout_identity` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:391` / `accept_local_test_terms` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:425` / `accept_published_terms` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:469` / `download_own_term_acceptance` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:136` / `onboarding_status` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:218` / `require_upload_ready` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:331` / `save_profile` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:385` / `accept_local_test_terms` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:419` / `accept_published_terms` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_onboarding.py:457` / `own_term_acceptances` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:163` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_signup.py:323` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_signup.py:165` / `signup_public_config` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_signup.py:216` / `request_email_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:236` / `start` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_signup.py:257` / `start` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:258` / `start` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:285` / `verify_email` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_signup.py:287` / `verify_email` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:310` / `_setup` | A | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/photographer_signup.py:313` / `_setup` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:325` / `setup` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_signup.py:333` / `complete` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_signup.py:343` / `complete` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:201` / `_lock_signup_identities` | A | query/ORM | `db.connection().get_execution_options().get('schema_translate_map', {}).get` | ver matriz |
| `backend/app/photographer_signup.py:204` / `_lock_signup_identities` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_signup.py:217` / `request_email_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:347` / `complete` | A | produtor | `Tenant` | ver matriz |
| `backend/app/photographer_signup.py:348` / `complete` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_signup.py:350` / `complete` | A | produtor | `AdminUser` | ver matriz |
| `backend/app/photographer_signup.py:353` / `complete` | A | query/ORM | `db.add_all` | ver matriz |
| `backend/app/photographer_signup.py:381` / `expire_signup_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_signup.py:391` / `expire_signup_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_signup.py:397` / `expire_signup_material` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:403` / `expire_signup_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_signup.py:412` / `expire_signup_material` | A | query/ORM | `db.delete` | ver matriz |
| `backend/app/photographer_signup.py:88` / `send_code` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/photographer_signup.py:204` / `_lock_signup_identities` | A | query/ORM | `text` | ver matriz |
| `backend/app/photographer_signup.py:221` / `request_email_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_signup.py:262` / `start` | A | produtor | `PhotographerSignup` | ver matriz |
| `backend/app/photographer_signup.py:264` / `start` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_signup.py:273` / `start` | A | efeito potencial | `services.send_code` | ver matriz |
| `backend/app/photographer_signup.py:352` / `complete` | A | produtor | `TenantAdmin` | ver matriz |
| `backend/app/photographer_signup.py:201` / `_lock_signup_identities` | A | query/ORM | `db.connection().get_execution_options().get` | ver matriz |
| `backend/app/photographer_signup.py:216` / `request_email_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:257` / `start` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:343` / `complete` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:353` / `complete` | A | produtor | `TenantCreditWallet` | ver matriz |
| `backend/app/photographer_signup.py:217` / `request_email_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:258` / `start` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:287` / `verify_email` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:313` / `_setup` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:397` / `expire_signup_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:403` / `expire_signup_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:221` / `request_email_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:381` / `expire_signup_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_signup.py:391` / `expire_signup_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_subdomain.py:68` / `reserve_address` | X | gate | `enable_domain_guard` | ver matriz |
| `backend/app/photographer_subdomain.py:69` / `reserve_address` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/photographer_subdomain.py:72` / `reserve_address` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_subdomain.py:72` / `reserve_address` | X | query/ORM | `select` | ver matriz |
| `backend/app/photographer_terms.py:88` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_terms.py:140` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_terms.py:154` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_terms.py:90` / `get_draft` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_terms.py:104` / `save_draft` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_terms.py:142` / `list_versions` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_terms.py:156` / `list_tenant_acceptances` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_terms.py:173` / `publish` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_terms.py:223` / `latest_published` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_terms.py:92` / `get_draft` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_terms.py:114` / `save_draft` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_terms.py:144` / `list_versions` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_terms.py:158` / `list_tenant_acceptances` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/photographer_terms.py:175` / `publish` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_terms.py:183` / `publish` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_terms.py:192` / `publish` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_terms.py:202` / `publish` | A | produtor | `PhotographerTermsVersion` | ver matriz |
| `backend/app/photographer_terms.py:210` / `publish` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_terms.py:238` / `render_terms` | A | efeito potencial | `rendered.replace` | ver matriz |
| `backend/app/photographer_terms.py:95` / `get_draft` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_terms.py:120` / `save_draft` | A | produtor | `PhotographerTermsDraft` | ver matriz |
| `backend/app/photographer_terms.py:121` / `save_draft` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_terms.py:223` / `latest_published` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_terms.py:114` / `save_draft` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_terms.py:144` / `list_versions` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_terms.py:158` / `list_tenant_acceptances` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_terms.py:175` / `publish` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_terms.py:183` / `publish` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_terms.py:192` / `publish` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp.py:80` / `_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp.py:85` / `_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp.py:92` / `_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp.py:95` / `_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp.py:96` / `_context` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp.py:100` / `_context` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_totp.py:125` / `begin` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp.py:132` / `begin` | A | produtor | `AdminTotpEnrollment` | ver matriz |
| `backend/app/photographer_totp.py:139` / `begin` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_totp.py:145` / `begin` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_totp.py:153` / `confirm` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp.py:166` / `confirm` | A | efeito potencial | `TotpSecretCipher.from_environment().decrypt` | ver matriz |
| `backend/app/photographer_totp.py:185` / `confirm` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_totp.py:190` / `confirm` | A | query/ORM | `db.add_all` | ver matriz |
| `backend/app/photographer_totp.py:195` / `confirm` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_totp.py:127` / `begin` | A | query/ORM | `db.delete` | ver matriz |
| `backend/app/photographer_totp.py:134` / `begin` | A | efeito potencial | `TotpSecretCipher.from_environment().encrypt` | ver matriz |
| `backend/app/photographer_totp.py:190` / `confirm` | A | produtor | `AdminTotpRecoveryCode` | ver matriz |
| `backend/app/photographer_totp.py:80` / `_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp.py:85` / `_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp.py:125` / `begin` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp.py:96` / `_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp.py:153` / `confirm` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp.py:185` / `confirm` | A | query/ORM | `update` | ver matriz |
| `backend/app/photographer_totp.py:92` / `_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp.py:95` / `_context` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp_support.py:68` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/photographer_totp_support.py:70` / `target` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_totp_support.py:84` / `_event` | A | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/photographer_totp_support.py:91` / `_event` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/photographer_totp_support.py:102` / `revoke_photographer_totp` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp_support.py:110` / `revoke_photographer_totp` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp_support.py:121` / `revoke_photographer_totp` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp_support.py:147` / `revoke_photographer_totp` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_totp_support.py:149` / `revoke_photographer_totp` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_totp_support.py:170` / `revoke` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/photographer_totp_support.py:98` / `revoke_photographer_totp` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp_support.py:117` / `revoke_photographer_totp` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/photographer_totp_support.py:153` / `revoke_photographer_totp` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/photographer_totp_support.py:65` / `_eligible` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/photographer_totp_support.py:72` / `target` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/photographer_totp_support.py:102` / `revoke_photographer_totp` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp_support.py:110` / `revoke_photographer_totp` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp_support.py:121` / `revoke_photographer_totp` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp_support.py:147` / `revoke_photographer_totp` | A | query/ORM | `update` | ver matriz |
| `backend/app/photographer_totp_support.py:149` / `revoke_photographer_totp` | A | query/ORM | `update` | ver matriz |
| `backend/app/photographer_totp_support.py:52` / `_eligible` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp_support.py:59` / `_eligible` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp_support.py:98` / `revoke_photographer_totp` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_totp_support.py:117` / `revoke_photographer_totp` | A | query/ORM | `select` | ver matriz |
| `backend/app/photographer_turnstile.py:87` / `verify` | A | produtor | `httpx.Client` | ver matriz |
| `backend/app/photographer_turnstile.py:108` / `verify` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/photographer_turnstile.py:110` / `verify` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/photographer_turnstile.py:101` / `verify` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/platform_backup/archive.py:170` / `seal_archive` | O | efeito potencial | `Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor` | ver matriz |
| `backend/app/platform_backup/archive.py:171` / `seal_archive` | O | efeito potencial | `encryptor.authenticate_additional_data` | ver matriz |
| `backend/app/platform_backup/archive.py:236` / `open_archive` | O | efeito potencial | `Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor` | ver matriz |
| `backend/app/platform_backup/archive.py:237` / `open_archive` | O | efeito potencial | `decryptor.authenticate_additional_data` | ver matriz |
| `backend/app/platform_backup/archive.py:98` / `describe_ciphertext` | O | query/ORM | `digest.update` | ver matriz |
| `backend/app/platform_backup/archive.py:178` / `emit` | O | query/ORM | `digest.update` | ver matriz |
| `backend/app/platform_backup/archive.py:193` / `seal_archive` | O | efeito potencial | `encryptor.finalize` | ver matriz |
| `backend/app/platform_backup/archive.py:243` / `open_archive` | O | query/ORM, efeito potencial | `decryptor.update` | ver matriz |
| `backend/app/platform_backup/archive.py:249` / `open_archive` | O | efeito potencial | `decryptor.finalize` | ver matriz |
| `backend/app/platform_backup/archive.py:189` / `seal_archive` | O | query/ORM, efeito potencial | `encryptor.update` | ver matriz |
| `backend/app/platform_backup/filesystem.py:36` / `directory` | O | efeito potencial | `os.open` | ver matriz |
| `backend/app/platform_backup/filesystem.py:57` / `open_file` | O | efeito potencial | `os.open` | ver matriz |
| `backend/app/platform_backup/filesystem.py:41` / `directory` | O | efeito potencial | `os.open` | ver matriz |
| `backend/app/platform_backup/payload.py:154` / `open_payload` | O | efeito potencial | `package.open` | ver matriz |
| `backend/app/platform_backup/payload.py:61` / `build_payload` | O | efeito potencial | `package.open` | ver matriz |
| `backend/app/platform_backup/payload.py:145` / `open_payload` | O | efeito potencial | `package.open` | ver matriz |
| `backend/app/platform_backup/payload.py:70` / `build_payload` | O | query/ORM | `digest.update` | ver matriz |
| `backend/app/platform_backup/payload.py:147` / `open_payload` | O | query/ORM | `digest.update` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:68` / `_attest` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:69` / `_attest` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:71` / `_attest` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:71` / `_attest` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:72` / `_attest` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:73` / `_attest` | O | query/ORM | `labels.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:74` / `_attest` | O | query/ORM | `labels.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:75` / `_attest` | O | query/ORM | `labels.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:76` / `_attest` | O | query/ORM | `labels.get` | ver matriz |
| `backend/app/platform_backup/postgres_sandbox.py:70` / `_attest` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:70` / `copy_workspace_backup` | O | efeito potencial | `store.upload` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:78` / `copy_workspace_backup` | O | efeito potencial | `store.open` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:127` / `restore_workspace_backup` | O | efeito potencial | `store.open` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:36` / `_record_once` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:37` / `_record_once` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:38` / `_record_once` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:119` / `restore_workspace_backup` | O | query/ORM | `item['payload']['data'].get` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:120` / `restore_workspace_backup` | O | query/ORM | `item['payload']['data'].get` | ver matriz |
| `backend/app/platform_backup/remote_copy.py:121` / `restore_workspace_backup` | O | query/ORM | `item['payload']['data'].get` | ver matriz |
| `backend/app/platform_backup/restore.py:100` / `record_restore` | O | query/ORM | `event['payload']['data'].get` | ver matriz |
| `backend/app/platform_backup/restore.py:101` / `record_restore` | O | query/ORM | `event['payload']['data'].get` | ver matriz |
| `backend/app/platform_backup/retention.py:81` / `plan_retention` | O | query/ORM | `keep.add` | ver matriz |
| `backend/app/platform_backup/retention.py:167` / `remove_redundant_local_copy` | O | efeito potencial | `os.unlink` | ver matriz |
| `backend/app/platform_backup/retention.py:77` / `plan_retention` | O | query/ORM | `seen.add` | ver matriz |
| `backend/app/platform_backup/retention.py:78` / `plan_retention` | O | query/ORM | `keep.add` | ver matriz |
| `backend/app/platform_backup/retention.py:110` / `_restore_proven` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/retention.py:110` / `_restore_proven` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/retention.py:114` / `_restore_proven` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/platform_backup/storage.py:32` / `_matches` | O | query/ORM | `digest.update` | ver matriz |
| `backend/app/platform_backup/storage.py:107` / `upload` | O | efeito potencial | `os.unlink` | ver matriz |
| `backend/app/platform_backup/worker.py:100` / `_artifact` | O | efeito potencial | `os.unlink` | ver matriz |
| `backend/app/platform_backup/worker.py:112` / `_artifact` | O | query/ORM | `expected.get` | ver matriz |
| `backend/app/platform_backup/worker.py:113` / `_artifact` | O | query/ORM | `expected.get` | ver matriz |
| `backend/app/platform_backup/worker.py:124` / `_record_once` | O | query/ORM | `item['payload']['data'].get` | ver matriz |
| `backend/app/platform_backup/worker.py:146` / `run_due` | O | efeito potencial | `store.upload` | ver matriz |
| `backend/app/platform_backup/worker.py:149` / `run_due` | O | efeito potencial | `store.open` | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py:74` / `create_workspace_backup_store` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py:88` / `create_workspace_backup_store` | O | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py:108` / `create_workspace_backup_store` | O | query/ORM | `token_data.get` | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py:109` / `create_workspace_backup_store` | O | query/ORM | `token_data.get` | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py:110` / `create_workspace_backup_store` | O | query/ORM | `token_data.get` | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py:111` / `create_workspace_backup_store` | O | query/ORM | `token_data.get` | ver matriz |
| `backend/app/platform_backup/workspace_credentials.py:74` / `create_workspace_backup_store` | O | query/ORM | `select` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:137` / `_find` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:138` / `_find` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:139` / `_find` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:140` / `_find` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:164` / `_download` | O | query/ORM | `remote.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:165` / `_download` | O | query/ORM | `remote.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:166` / `_download` | O | query/ORM | `remote.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:106` / `_find` | O | query/ORM | `params.update` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:111` / `_find` | O | query/ORM | `transport.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:218` / `open` | O | efeito potencial | `self._download` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:249` / `upload` | O | efeito potencial | `uploader` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:122` / `_find` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:123` / `_find` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:124` / `_find` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:144` / `_find` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:145` / `_find` | O | query/ORM | `item.get` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:234` / `upload` | O | efeito potencial | `self._download` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:238` / `upload` | O | query/ORM | `digest.update` | ver matriz |
| `backend/app/platform_backup/workspace_store.py:200` / `_download` | O | query/ORM | `digest.update` | ver matriz |
| `backend/app/platform_console.py:186` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:198` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:208` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:215` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:533` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:615` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:854` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:977` / `<módulo>` | A | query/ORM | `router.get` | ver matriz |
| `backend/app/platform_console.py:74` / `require_console_owner` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/platform_console.py:80` / `_prior_admin_action_event` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:188` / `capabilities` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:202` / `tenants` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:210` / `detail` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:219` / `tenant_closure_status` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:232` / `reduce_tenant_profile` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:294` / `request_tenant_media_deletion` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:378` / `retry_tenant_media_deletion` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:469` / `request_tenant_closure_recovery` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:542` / `tenant_closure_recovery_status` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:561` / `reopen_tenant_account` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:617` / `sources` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:685` / `_status_event` | A | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/platform_console.py:690` / `_status_event` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/platform_console.py:709` / `change_tenant_status` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:711` / `change_tenant_status` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:717` / `change_tenant_status` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:762` / `activate_tenant_hostname` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:764` / `activate_tenant_hostname` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:774` / `activate_tenant_hostname` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:832` / `status` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:845` / `activate_hostname` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:858` / `media_archive_recovery_pricing` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:871` / `update_media_archive_recovery_pricing` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:926` / `retry_media_archive_recovery` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:980` / `audit_events` | A | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/platform_console.py:240` / `reduce_tenant_profile` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:273` / `reduce_tenant_profile` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/platform_console.py:304` / `request_tenant_media_deletion` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:351` / `request_tenant_media_deletion` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/platform_console.py:388` / `retry_tenant_media_deletion` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:436` / `retry_tenant_media_deletion` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:442` / `retry_tenant_media_deletion` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/platform_console.py:471` / `request_tenant_closure_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:485` / `request_tenant_closure_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:490` / `request_tenant_closure_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:574` / `reopen_tenant_account` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:620` / `sources` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:873` / `update_media_archive_recovery_pricing` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:883` / `update_media_archive_recovery_pricing` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:932` / `retry_media_archive_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:945` / `retry_media_archive_recovery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:142` / `tenant_directory` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:161` / `tenant_directory` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/platform_console.py:171` / `tenant_summary` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/platform_console.py:175` / `tenant_summary` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/platform_console.py:273` / `reduce_tenant_profile` | A | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/platform_console.py:351` / `request_tenant_media_deletion` | A | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/platform_console.py:418` / `retry_tenant_media_deletion` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/platform_console.py:442` / `retry_tenant_media_deletion` | A | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/platform_console.py:80` / `_prior_admin_action_event` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:175` / `tenant_summary` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:711` / `change_tenant_status` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:774` / `activate_tenant_hostname` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:982` / `audit_events` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:985` / `audit_events` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/platform_console.py:436` / `retry_tenant_media_deletion` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:471` / `request_tenant_closure_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:490` / `request_tenant_closure_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:932` / `retry_media_archive_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:171` / `tenant_summary` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:709` / `change_tenant_status` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:620` / `sources` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:873` / `update_media_archive_recovery_pricing` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:147` / `tenant_directory` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:717` / `change_tenant_status` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:762` / `activate_tenant_hostname` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:764` / `activate_tenant_hostname` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:135` / `tenant_directory` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:176` / `tenant_summary` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:177` / `tenant_summary` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:240` / `reduce_tenant_profile` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:304` / `request_tenant_media_deletion` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:388` / `retry_tenant_media_deletion` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:485` / `request_tenant_closure_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:574` / `reopen_tenant_account` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:883` / `update_media_archive_recovery_pricing` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:945` / `retry_media_archive_recovery` | A | query/ORM | `select` | ver matriz |
| `backend/app/platform_console.py:418` / `retry_tenant_media_deletion` | A | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:33` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:64` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:83` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:159` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:72` / `galleries` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/api.py:101` / `gallery_progress` | P | query/ORM | `counts.update` | ver matriz |
| `backend/app/preview_adjustment/api.py:130` / `enqueue_gallery` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:37` / `configuration` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:57` / `save_configuration` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:92` / `gallery_progress` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:149` / `enqueue_gallery` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/preview_adjustment/api.py:168` / `compare` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/api.py:114` / `gallery_progress` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/api.py:150` / `enqueue_gallery` | P | efeito potencial | `enqueue` | ver matriz |
| `backend/app/preview_adjustment/api.py:163` / `compare` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:101` / `gallery_progress` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/api.py:169` / `compare` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:95` / `gallery_progress` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:73` / `galleries` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:103` / `gallery_progress` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:137` / `enqueue_gallery` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:63` / `cleanup` | P | gate | `require_single_tenant` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:64` / `cleanup` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:69` / `cleanup` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:73` / `cleanup` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:75` / `cleanup` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:83` / `cleanup` | P | gate | `require_single_tenant` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:84` / `cleanup` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:81` / `cleanup` | P | gate | `require_single_tenant` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:82` / `cleanup` | P | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:84` / `cleanup` | P | query/ORM | `delete` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:64` / `cleanup` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:69` / `cleanup` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:73` / `cleanup` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:75` / `cleanup` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/engine.py:64` / `render` | P | efeito potencial | `Image.open` | ver matriz |
| `backend/app/preview_adjustment/service.py:57` / `settings` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:64` / `settings` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:71` / `configure` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:73` / `configure` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:108` / `inputs` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:111` / `inputs` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:127` / `inputs` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:146` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:149` / `photo_active` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:165` / `adjustment_for` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:166` / `adjustment_for` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:174` / `private_facial_job_completed` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:189` / `enqueue` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:190` / `enqueue` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:195` / `enqueue` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:201` / `enqueue` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:229` / `enqueue` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:288` / `adjusted_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:293` / `adjusted_path` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:80` / `configure` | P | produtor | `GalleryPreviewSettings` | ver matriz |
| `backend/app/preview_adjustment/service.py:88` / `configure` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/preview_adjustment/service.py:159` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:206` / `enqueue` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:238` / `enqueue` | P | produtor | `PreviewAdjustment` | ver matriz |
| `backend/app/preview_adjustment/service.py:239` / `enqueue` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/preview_adjustment/service.py:249` / `enqueue_after_derivatives` | P | efeito potencial | `enqueue` | ver matriz |
| `backend/app/preview_adjustment/service.py:289` / `adjusted_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:303` / `presentation_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:340` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:341` / `process_one` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:343` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:366` / `process_one` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:58` / `settings` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:114` / `inputs` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/preview_adjustment/service.py:144` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:310` / `presentation_path` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:316` / `presentation_path` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:385` / `process_one` | P | produtor | `BrandingSettings` | ver matriz |
| `backend/app/preview_adjustment/service.py:404` / `process_one` | P | efeito potencial | `Image.open` | ver matriz |
| `backend/app/preview_adjustment/service.py:413` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:414` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:422` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:429` / `process_one` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:447` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:456` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:457` / `process_one` | P | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/preview_adjustment/service.py:190` / `enqueue` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:329` / `process_one` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:419` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:423` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:480` / `process_one` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:467` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:468` / `process_one` | P | efeito potencial | `previous.unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:475` / `process_one` | P | efeito potencial | `output.with_suffix('.tmp').unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:476` / `process_one` | P | efeito potencial | `output.unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:74` / `configure` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:128` / `inputs` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:150` / `photo_active` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:166` / `adjustment_for` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:195` / `enqueue` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:201` / `enqueue` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:415` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:207` / `enqueue` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:115` / `inputs` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:175` / `private_facial_job_completed` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:422` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:420` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:424` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:481` / `process_one` | P | query/ORM | `update` | ver matriz |
| `backend/app/preview_adjustment/service.py:344` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:330` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:64` / `_insert_once` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:87` / `ensure_private_photo_reference` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:88` / `ensure_private_photo_reference` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:107` / `ensure_private_photo_reference` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:134` / `derive_client_selection` | G | gate | `client_tenant_id` | ver matriz |
| `backend/app/private_derivation.py:136` / `derive_client_selection` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:137` / `derive_client_selection` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:138` / `derive_client_selection` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:139` / `derive_client_selection` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:233` / `derive_admin_gallery` | G | gate | `client_tenant_id` | ver matriz |
| `backend/app/private_derivation.py:235` / `derive_admin_gallery` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:236` / `derive_admin_gallery` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:99` / `ensure_private_photo_reference` | G | produtor | `DerivedGalleryPhoto` | ver matriz |
| `backend/app/private_derivation.py:112` / `ensure_private_photo_reference` | G | produtor | `DerivedGalleryPhotoOrigin` | ver matriz |
| `backend/app/private_derivation.py:147` / `derive_client_selection` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:206` / `derive_client_selection` | G | produtor | `PhotoSelection` | ver matriz |
| `backend/app/private_derivation.py:68` / `_insert_once` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_derivation.py:92` / `ensure_private_photo_reference` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:72` / `_insert_once` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:117` / `ensure_private_photo_reference` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:199` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:140` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:148` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:136` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_fields.py:29` / `encrypt_private_field` | A | efeito potencial | `_encrypt_private_value` | ver matriz |
| `backend/app/private_fields.py:33` / `encrypt_private_document` | A | efeito potencial | `_encrypt_private_value` | ver matriz |
| `backend/app/private_fields.py:41` / `_encrypt_private_value` | A | efeito potencial | `AESGCM(_key()).encrypt` | ver matriz |
| `backend/app/private_fields.py:46` / `decrypt_private_field` | A | efeito potencial | `_decrypt_private_value` | ver matriz |
| `backend/app/private_fields.py:50` / `decrypt_private_document` | A | efeito potencial | `_decrypt_private_value` | ver matriz |
| `backend/app/private_fields.py:59` / `_decrypt_private_value` | A | efeito potencial | `AESGCM(_key()).decrypt(raw[:12], raw[12:], aad).decode` | ver matriz |
| `backend/app/private_fields.py:59` / `_decrypt_private_value` | A | efeito potencial | `AESGCM(_key()).decrypt` | ver matriz |
| `backend/app/private_folder_overview.py:68` / `private_folder_overview` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_folder_overview.py:22` / `private_folder_overview` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_folder_overview.py:41` / `private_folder_overview` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_folder_overview.py:65` / `private_folder_overview` | G | query/ORM | `media_states.get` | ver matriz |
| `backend/app/private_folder_overview.py:69` / `private_folder_overview` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_folder_overview.py:42` / `private_folder_overview` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_folder_overview.py:23` / `private_folder_overview` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:43` / `remove_client_selection_and_close_if_empty` | L | gate | `client_tenant_id` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:48` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:67` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:68` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:89` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:115` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:121` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:138` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:140` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:146` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:152` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:76` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:98` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:101` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:136` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:110` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `db.delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:49` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `select` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:69` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `select` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:138` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:141` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:147` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:77` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `select` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:136` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `delete` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:90` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `select` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:116` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `select` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:122` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `select` | ver matriz |
| `backend/app/private_gallery_lifecycle.py:102` / `remove_client_selection_and_close_if_empty` | L | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:52` / `membership_for_client` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:96` / `operational_galleries_for_client` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_membership.py:110` / `client_has_operational_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:111` / `client_has_operational_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:114` / `client_has_operational_membership` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:123` / `client_has_operational_membership` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:138` / `_legacy_gallery_for_client` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:193` / `ensure_private_membership` | G | gate | `require_client_owner` | ver matriz |
| `backend/app/private_membership.py:81` / `operational_galleries_for_client` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_membership.py:203` / `ensure_private_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:45` / `membership_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:89` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:162` / `_create_legacy_compatible_gallery` | G | produtor | `DerivedGallery` | ver matriz |
| `backend/app/private_membership.py:168` / `_create_legacy_compatible_gallery` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_membership.py:229` / `ensure_private_membership` | G | produtor | `DerivedGalleryMembership` | ver matriz |
| `backend/app/private_membership.py:236` / `ensure_private_membership` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_membership.py:256` / `ensure_private_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:115` / `client_has_operational_membership` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:124` / `client_has_operational_membership` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:139` / `_legacy_gallery_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:44` / `membership_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:67` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:85` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:63` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:28` / `batch_for` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:29` / `batch_for` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_upload_batches.py:40` / `folder_batch_for` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:41` / `folder_batch_for` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_upload_batches.py:68` / `create_batch` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:69` / `create_batch` | G | produtor | `PrivateUploadBatch` | ver matriz |
| `backend/app/private_upload_batches.py:70` / `create_batch` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_upload_batches.py:76` / `create_folder_batch` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:79` / `create_folder_batch` | G | produtor | `PrivateUploadBatch` | ver matriz |
| `backend/app/private_upload_batches.py:83` / `create_folder_batch` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_upload_batches.py:117` / `process_ready_batches` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_upload_batches.py:52` / `batch_payload` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_upload_batches.py:96` / `close_batch` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_upload_batches.py:123` / `process_ready_batches` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:126` / `process_ready_batches` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_upload_batches.py:168` / `process_ready_batches` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:93` / `close_batch` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_upload_batches.py:142` / `process_ready_batches` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_upload_batches.py:144` / `process_ready_batches` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_upload_batches.py:63` / `batch_payload` | G | efeito potencial | `logical_upload_key` | ver matriz |
| `backend/app/private_upload_batches.py:124` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:145` / `process_ready_batches` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_upload_batches.py:160` / `process_ready_batches` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_upload_batches.py:126` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:149` / `process_ready_batches` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_upload_batches.py:152` / `process_ready_batches` | G | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/private_upload_batches.py:29` / `batch_for` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:41` / `folder_batch_for` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:93` / `close_batch` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:112` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:129` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:52` / `batch_payload` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:117` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/provision_installation_operator.py:35` / `provision_operator` | O | query/ORM | `db.get` | ver matriz |
| `backend/app/provision_installation_operator.py:42` / `provision_operator` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provision_installation_operator.py:65` / `provision_operator` | O | query/ORM | `db.add` | ver matriz |
| `backend/app/provision_installation_operator.py:30` / `provision_operator` | O | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `backend/app/provision_installation_operator.py:31` / `provision_operator` | O | query/ORM | `translation.get` | ver matriz |
| `backend/app/provision_installation_operator.py:34` / `provision_operator` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/provision_installation_operator.py:41` / `provision_operator` | O | gate | `require_admin_tenant` | ver matriz |
| `backend/app/provision_installation_operator.py:53` / `provision_operator` | O | gate | `require_admin_tenant` | ver matriz |
| `backend/app/provision_installation_operator.py:65` / `provision_operator` | O | produtor | `AuditEvent` | ver matriz |
| `backend/app/provision_installation_operator.py:34` / `provision_operator` | O | query/ORM | `text` | ver matriz |
| `backend/app/provision_installation_operator.py:55` / `provision_operator` | O | produtor | `InstallationOperator` | ver matriz |
| `backend/app/provision_installation_operator.py:56` / `provision_operator` | O | query/ORM | `db.add` | ver matriz |
| `backend/app/provision_installation_operator.py:42` / `provision_operator` | O | query/ORM | `select` | ver matriz |
| `backend/app/provision_photographer.py:51` / `existing_admin_owner` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/provision_photographer.py:61` / `plan_provisioning` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/provision_photographer.py:72` / `plan_provisioning` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provision_photographer.py:113` / `provision_photographer` | A | produtor | `AdminUser` | ver matriz |
| `backend/app/provision_photographer.py:116` / `provision_photographer` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/provision_photographer.py:39` / `existing_admin_by_email` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provision_photographer.py:46` / `existing_admin_owner` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provision_photographer.py:68` / `plan_provisioning` | A | gate | `existing_admin_owner` | ver matriz |
| `backend/app/provision_photographer.py:95` / `provision_photographer` | A | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `backend/app/provision_photographer.py:103` / `provision_photographer` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/provision_photographer.py:110` / `provision_photographer` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/provision_photographer.py:112` / `provision_photographer` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/provision_photographer.py:115` / `provision_photographer` | A | produtor | `TenantAdmin` | ver matriz |
| `backend/app/provision_photographer.py:100` / `provision_photographer` | A | query/ORM | `translation.get` | ver matriz |
| `backend/app/provision_photographer.py:103` / `provision_photographer` | A | query/ORM | `text` | ver matriz |
| `backend/app/provision_photographer.py:110` / `provision_photographer` | A | produtor | `Tenant` | ver matriz |
| `backend/app/provision_photographer.py:112` / `provision_photographer` | A | produtor | `TenantCreditWallet` | ver matriz |
| `backend/app/provision_photographer.py:82` / `validate_new_credentials` | A | efeito potencial | `totp_secret.replace` | ver matriz |
| `backend/app/provision_photographer.py:72` / `plan_provisioning` | A | query/ORM | `select` | ver matriz |
| `backend/app/provision_photographer.py:39` / `existing_admin_by_email` | A | query/ORM | `select` | ver matriz |
| `backend/app/provision_photographer.py:46` / `existing_admin_owner` | A | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:60` / `active_capability_by_id` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:70` / `active_registration` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:137` / `apply_public_gallery_access` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/public_gallery_access.py:140` / `apply_public_gallery_access` | G | gate | `owned_record` | ver matriz |
| `backend/app/public_gallery_access.py:207` / `require_public_gallery_browsing` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:303` / `authorized_canonical_photo` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:54` / `active_capability_by_id` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/public_gallery_access.py:110` / `client_otp_delivery_allowed` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:291` / `authorized_canonical_folders` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:207` / `require_public_gallery_browsing` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:229` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:252` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:259` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:61` / `active_capability_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:71` / `active_registration` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:110` / `client_otp_delivery_allowed` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:226` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:234` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/push_subscriptions.py:83` / `installation_key` | N | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/push_subscriptions.py:93` / `revoke_installation` | N | gate | `require_push_session` | ver matriz |
| `backend/app/push_subscriptions.py:94` / `revoke_installation` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/push_subscriptions.py:109` / `detach_previous_identity` | N | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/push_subscriptions.py:112` / `detach_previous_identity` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/push_subscriptions.py:122` / `require_push_session` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/push_subscriptions.py:123` / `require_push_session` | N | gate | `owned_record` | ver matriz |
| `backend/app/push_subscriptions.py:139` / `subscribe` | N | gate | `require_push_session` | ver matriz |
| `backend/app/push_subscriptions.py:145` / `subscribe` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/push_subscriptions.py:156` / `subscribe` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/push_subscriptions.py:173` / `subscribe` | N | efeito potencial | `cipher().encrypt(json.dumps({'id': str(item.id), 'role': item.role, 'subject_id': str(item.subject_id), 'generation': item.generation, 'subscription': data}).encode()).decode` | ver matriz |
| `backend/app/push_subscriptions.py:106` / `detach_previous_identity` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/push_subscriptions.py:141` / `subscribe` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/push_subscriptions.py:149` / `subscribe` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/push_subscriptions.py:163` / `subscribe` | N | produtor | `PushSubscription` | ver matriz |
| `backend/app/push_subscriptions.py:165` / `subscribe` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/push_subscriptions.py:79` / `validate_subscription` | N | query/ORM | `payload.get` | ver matriz |
| `backend/app/push_subscriptions.py:105` / `detach_previous_identity` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/push_subscriptions.py:124` / `require_push_session` | N | efeito potencial | `current.expires_at.replace` | ver matriz |
| `backend/app/push_subscriptions.py:129` / `require_push_session` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/push_subscriptions.py:173` / `subscribe` | N | efeito potencial | `cipher().encrypt` | ver matriz |
| `backend/app/push_subscriptions.py:183` / `decrypt_subscription` | N | efeito potencial | `cipher().decrypt` | ver matriz |
| `backend/app/push_subscriptions.py:69` / `validate_subscription` | N | query/ORM | `payload.get` | ver matriz |
| `backend/app/push_subscriptions.py:105` / `detach_previous_identity` | N | gate | `require_admin_tenant` | ver matriz |
| `backend/app/push_subscriptions.py:134` / `require_push_session` | N | gate | `owned_record` | ver matriz |
| `backend/app/push_subscriptions.py:156` / `subscribe` | N | query/ORM | `select` | ver matriz |
| `backend/app/push_subscriptions.py:183` / `decrypt_subscription` | N | efeito potencial | `item.encrypted_subscription.encode` | ver matriz |
| `backend/app/push_subscriptions.py:94` / `revoke_installation` | N | query/ORM | `select` | ver matriz |
| `backend/app/push_subscriptions.py:105` / `detach_previous_identity` | N | query/ORM | `select` | ver matriz |
| `backend/app/push_subscriptions.py:112` / `detach_previous_identity` | N | query/ORM | `select` | ver matriz |
| `backend/app/push_subscriptions.py:130` / `require_push_session` | N | gate | `require_admin_tenant` | ver matriz |
| `backend/app/push_subscriptions.py:145` / `subscribe` | N | query/ORM | `select` | ver matriz |
| `backend/app/push_subscriptions.py:141` / `subscribe` | N | query/ORM | `select` | ver matriz |
| `backend/app/push_subscriptions.py:149` / `subscribe` | N | query/ORM | `select` | ver matriz |
| `backend/app/seed_admin.py:34` / `seed_admin` | A | gate | `require_single_tenant` | ver matriz |
| `backend/app/seed_admin.py:35` / `seed_admin` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/seed_admin.py:39` / `seed_admin` | A | produtor | `AdminUser` | ver matriz |
| `backend/app/seed_admin.py:46` / `seed_admin` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/seed_admin.py:32` / `seed_admin` | A | gate | `existing_admin_owner` | ver matriz |
| `backend/app/seed_admin.py:35` / `seed_admin` | A | query/ORM | `select` | ver matriz |
| `backend/app/seed_admin.py:45` / `seed_admin` | A | produtor | `TenantAdmin` | ver matriz |
| `backend/app/statistics_report.py:43` / `_payment` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:53` / `_payment` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:60` / `_payment` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:103` / `commercial_report` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/statistics_report.py:222` / `commercial_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:261` / `commercial_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:262` / `commercial_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:86` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:89` / `commercial_report` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/statistics_report.py:124` / `commercial_report` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/statistics_report.py:153` / `commercial_report` | O | query/ORM | `purchased_selection_keys.update` | ver matriz |
| `backend/app/statistics_report.py:195` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:198` / `commercial_report` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/statistics_report.py:203` / `commercial_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:229` / `commercial_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:232` / `commercial_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/statistics_report.py:120` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:138` / `commercial_report` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/statistics_report.py:238` / `commercial_report` | O | efeito potencial | `expiry.replace` | ver matriz |
| `backend/app/statistics_report.py:43` / `_payment` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:53` / `_payment` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:60` / `_payment` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:152` / `commercial_report` | O | query/ORM | `revenue_by_day.get` | ver matriz |
| `backend/app/statistics_report.py:187` / `commercial_report` | O | query/ORM | `by_gallery.get` | ver matriz |
| `backend/app/statistics_report.py:188` / `commercial_report` | O | query/ORM | `by_folder.get` | ver matriz |
| `backend/app/statistics_report.py:261` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:262` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:89` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:203` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:229` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:232` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:138` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/statistics_report.py:222` / `commercial_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/storage_metrics.py:116` / `_owned_path` | X | gate | `media_namespace` | ver matriz |
| `backend/app/storage_metrics.py:119` / `_owned_path` | X | gate | `media_namespace` | ver matriz |
| `backend/app/storage_metrics.py:172` / `measure_owned_photo_storage` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/storage_metrics.py:135` / `_measure_owned_photo_storage` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/storage_metrics.py:141` / `_measure_owned_photo_storage` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/storage_metrics.py:145` / `_measure_owned_photo_storage` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/storage_metrics.py:180` / `measure_owned_photo_storage` | X | query/ORM | `_owned_cache.get` | ver matriz |
| `backend/app/storage_metrics.py:194` / `measure_owned_photo_storage` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/storage_metrics.py:138` / `_measure_owned_photo_storage` | X | query/ORM | `paths.add` | ver matriz |
| `backend/app/storage_metrics.py:139` / `_measure_owned_photo_storage` | X | query/ORM | `paths.update` | ver matriz |
| `backend/app/storage_metrics.py:144` / `_measure_owned_photo_storage` | X | query/ORM | `paths.add` | ver matriz |
| `backend/app/storage_metrics.py:150` / `_measure_owned_photo_storage` | X | query/ORM | `paths.update` | ver matriz |
| `backend/app/storage_metrics.py:157` / `_measure_owned_photo_storage` | X | query/ORM | `seen.add` | ver matriz |
| `backend/app/storage_metrics.py:176` / `measure_owned_photo_storage` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/storage_metrics.py:135` / `_measure_owned_photo_storage` | X | query/ORM | `select` | ver matriz |
| `backend/app/storage_metrics.py:141` / `_measure_owned_photo_storage` | X | query/ORM | `select` | ver matriz |
| `backend/app/storage_metrics.py:145` / `_measure_owned_photo_storage` | X | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/access.py:12` / `is_owner` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/access.py:26` / `permissions` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/system_monitor/access.py:26` / `permissions` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/access.py:12` / `is_owner` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:15` / `signal` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/activity.py:45` / `session_aggregate` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:65` / `page` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/activity.py:127` / `totals` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/activity.py:65` / `page` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:127` / `totals` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:129` / `totals` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/activity.py:130` / `totals` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/activity.py:14` / `signal` | O | query/ORM | `insert` | ver matriz |
| `backend/app/system_monitor/activity.py:85` / `page` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:108` / `page` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/activity.py:117` / `page` | O | query/ORM | `item.update` | ver matriz |
| `backend/app/system_monitor/activity.py:135` / `totals` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/activity.py:91` / `page` | O | efeito potencial | `query.replace('\\', '\\\\').replace('%', '\\%').replace` | ver matriz |
| `backend/app/system_monitor/activity.py:34` / `session_aggregate` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:38` / `session_aggregate` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:102` / `page` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/activity.py:118` / `page` | O | query/ORM | `issues.get` | ver matriz |
| `backend/app/system_monitor/activity.py:129` / `totals` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:130` / `totals` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:91` / `page` | O | efeito potencial | `query.replace('\\', '\\\\').replace` | ver matriz |
| `backend/app/system_monitor/activity.py:56` / `session_aggregate` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:41` / `session_aggregate` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:91` / `page` | O | efeito potencial | `query.replace` | ver matriz |
| `backend/app/system_monitor/activity.py:96` / `page` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:108` / `page` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:135` / `totals` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:77` / `page` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/activity.py:78` / `page` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/config.py:8` / `utc` | O | efeito potencial | `value.replace` | ver matriz |
| `backend/app/system_monitor/grants.py:20` / `establish_owner` | O | query/ORM | `db.get` | ver matriz |
| `backend/app/system_monitor/grants.py:23` / `establish_owner` | O | gate | `require_admin_tenant` | ver matriz |
| `backend/app/system_monitor/grants.py:24` / `establish_owner` | O | query/ORM | `db.get` | ver matriz |
| `backend/app/system_monitor/grants.py:36` / `change_grants` | O | query/ORM | `db.get` | ver matriz |
| `backend/app/system_monitor/grants.py:28` / `establish_owner` | O | query/ORM | `db.add` | ver matriz |
| `backend/app/system_monitor/grants.py:45` / `change_grants` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/grants.py:28` / `establish_owner` | O | produtor | `PlatformOwner` | ver matriz |
| `backend/app/system_monitor/grants.py:41` / `change_grants` | O | gate | `require_admin_tenant` | ver matriz |
| `backend/app/system_monitor/grants.py:43` / `change_grants` | O | query/ORM | `insert` | ver matriz |
| `backend/app/system_monitor/host.py:36` / `read_host` | O | efeito potencial | `Path(path).open` | ver matriz |
| `backend/app/system_monitor/host_collect.py:62` / `collect` | O | query/ORM | `result.update` | ver matriz |
| `backend/app/system_monitor/host_collect.py:75` / `atomic_write` | O | efeito potencial | `os.replace` | ver matriz |
| `backend/app/system_monitor/host_collect.py:44` / `rates` | O | query/ORM | `second.get` | ver matriz |
| `backend/app/system_monitor/host_collect.py:44` / `rates` | O | query/ORM | `first.get` | ver matriz |
| `backend/app/system_monitor/host_collect.py:64` / `collect` | O | query/ORM | `memory.get` | ver matriz |
| `backend/app/system_monitor/host_collect.py:64` / `collect` | O | query/ORM | `memory.get` | ver matriz |
| `backend/app/system_monitor/host_collect.py:78` / `atomic_write` | O | efeito potencial | `os.unlink` | ver matriz |
| `backend/app/system_monitor/host_collect.py:24` / `counters` | O | query/ORM | `values.update` | ver matriz |
| `backend/app/system_monitor/host_collect.py:29` / `counters` | O | query/ORM | `values.update` | ver matriz |
| `backend/app/system_monitor/incidents.py:62` / `signals_for` | O | query/ORM | `capacity.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:67` / `signals_for` | O | query/ORM | `capacity.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:70` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:90` / `signals_for` | O | query/ORM | `(sample.get('jobs') or {}).get` | ver matriz |
| `backend/app/system_monitor/incidents.py:27` / `evaluate` | O | query/ORM | `db.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:61` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:68` / `signals_for` | O | query/ORM | `pool.get('checked_out', {}).get` | ver matriz |
| `backend/app/system_monitor/incidents.py:68` / `signals_for` | O | query/ORM | `pool.get('potential_max', {}).get` | ver matriz |
| `backend/app/system_monitor/incidents.py:72` / `signals_for` | O | query/ORM | `host.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:81` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:94` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:74` / `signals_for` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:74` / `signals_for` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:77` / `signals_for` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:78` / `signals_for` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:78` / `signals_for` | O | query/ORM | `data.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:81` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:86` / `signals_for` | O | query/ORM | `worker.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:87` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:101` / `signals_for` | O | query/ORM | `(sample.get('jobs') or {}).get` | ver matriz |
| `backend/app/system_monitor/incidents.py:104` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:111` / `incident_rows` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/system_monitor/incidents.py:113` / `incident_rows` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/system_monitor/incidents.py:33` / `evaluate` | O | produtor | `MonitorIncident` | ver matriz |
| `backend/app/system_monitor/incidents.py:35` / `evaluate` | O | query/ORM | `db.add` | ver matriz |
| `backend/app/system_monitor/incidents.py:49` / `evaluate` | O | query/ORM | `db.add` | ver matriz |
| `backend/app/system_monitor/incidents.py:68` / `signals_for` | O | query/ORM | `pool.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:68` / `signals_for` | O | query/ORM | `pool.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:71` / `signals_for` | O | query/ORM | `host.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:90` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:49` / `evaluate` | O | produtor | `MonitorTransition` | ver matriz |
| `backend/app/system_monitor/incidents.py:71` / `signals_for` | O | query/ORM | `host.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:84` / `signals_for` | O | query/ORM | `capacity.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:119` / `incident_rows` | O | query/ORM | `row.evidence.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:119` / `incident_rows` | O | query/ORM | `row.evidence.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:121` / `incident_rows` | O | query/ORM | `row.evidence.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:121` / `incident_rows` | O | query/ORM | `row.evidence.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:101` / `signals_for` | O | query/ORM | `sample.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:98` / `signals_for` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/incidents.py:111` / `incident_rows` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/incidents.py:113` / `incident_rows` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/report.py:41` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:49` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:112` / `build_report` | O | efeito potencial | `instant.replace` | ver matriz |
| `backend/app/system_monitor/report.py:114` / `build_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/report.py:51` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:52` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:53` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:65` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:67` / `safe_sample` | O | query/ORM | `payload.get('storage', {}).get` | ver matriz |
| `backend/app/system_monitor/report.py:68` / `safe_sample` | O | query/ORM | `payload.get('storage', {}).get` | ver matriz |
| `backend/app/system_monitor/report.py:94` / `sufficient_coverage` | O | query/ORM | `sample['host'].get` | ver matriz |
| `backend/app/system_monitor/report.py:116` / `build_report` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/report.py:46` / `safe_sample` | O | query/ORM | `host.get` | ver matriz |
| `backend/app/system_monitor/report.py:50` / `safe_sample` | O | query/ORM | `jobs.get` | ver matriz |
| `backend/app/system_monitor/report.py:53` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:54` / `safe_sample` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:79` / `snapshot_history` | O | query/ORM | `db.scalars` | ver matriz |
| `backend/app/system_monitor/report.py:96` / `sufficient_coverage` | O | query/ORM | `host.get` | ver matriz |
| `backend/app/system_monitor/report.py:101` / `sufficient_coverage` | O | query/ORM | `sample['database_waits'].get` | ver matriz |
| `backend/app/system_monitor/report.py:103` / `sufficient_coverage` | O | query/ORM | `sample['quality'].get` | ver matriz |
| `backend/app/system_monitor/report.py:104` / `sufficient_coverage` | O | query/ORM | `sample['quality'].get` | ver matriz |
| `backend/app/system_monitor/report.py:66` / `safe_sample` | O | query/ORM | `original.get` | ver matriz |
| `backend/app/system_monitor/report.py:67` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:68` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:25` / `counts` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:25` / `counts` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:34` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:57` / `safe_sample` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:58` / `safe_sample` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:59` / `safe_sample` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:60` / `safe_sample` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:61` / `safe_sample` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:97` / `sufficient_coverage` | O | query/ORM | `host.get` | ver matriz |
| `backend/app/system_monitor/report.py:26` / `counts` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:61` / `safe_sample` | O | query/ORM | `row.get` | ver matriz |
| `backend/app/system_monitor/report.py:87` / `snapshot_history` | O | query/ORM | `capacity.get` | ver matriz |
| `backend/app/system_monitor/report.py:114` / `build_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/report.py:76` / `snapshot_history` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/report.py:116` / `build_report` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/report.py:38` / `safe_sample` | O | query/ORM | `payload.get` | ver matriz |
| `backend/app/system_monitor/report.py:79` / `snapshot_history` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/routes.py:47` / `<módulo>` | O | query/ORM | `router.get` | ver matriz |
| `backend/app/system_monitor/routes.py:55` / `<módulo>` | O | query/ORM | `router.get` | ver matriz |
| `backend/app/system_monitor/routes.py:62` / `<módulo>` | O | query/ORM | `router.get` | ver matriz |
| `backend/app/system_monitor/routes.py:78` / `<módulo>` | O | query/ORM | `router.get` | ver matriz |
| `backend/app/system_monitor/routes.py:86` / `<módulo>` | O | query/ORM | `router.get` | ver matriz |
| `backend/app/system_monitor/routes.py:107` / `<módulo>` | O | query/ORM | `router.get` | ver matriz |
| `backend/app/system_monitor/routes.py:49` / `capabilities` | O | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/system_monitor/routes.py:57` / `summary` | O | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/system_monitor/routes.py:67` / `tree` | O | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/system_monitor/routes.py:80` / `incidents` | O | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/system_monitor/routes.py:109` / `activity_policy` | O | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/system_monitor/routes.py:118` / `activity` | O | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/system_monitor/runtime.py:53` / `collect` | O | efeito potencial | `instant.replace` | ver matriz |
| `backend/app/system_monitor/runtime.py:63` / `collect` | O | query/ORM | `db.get` | ver matriz |
| `backend/app/system_monitor/runtime.py:71` / `collect` | O | query/ORM | `payload.update` | ver matriz |
| `backend/app/system_monitor/runtime.py:74` / `collect` | O | query/ORM | `db.add` | ver matriz |
| `backend/app/system_monitor/runtime.py:37` / `flush` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/runtime.py:74` / `collect` | O | produtor | `MonitorSample` | ver matriz |
| `backend/app/system_monitor/runtime.py:59` / `collect` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/runtime.py:34` / `flush` | O | query/ORM | `insert` | ver matriz |
| `backend/app/system_monitor/runtime.py:60` / `collect` | O | query/ORM | `text` | ver matriz |
| `backend/app/system_monitor/sources.py:32` / `job_counts` | O | query/ORM | `groups.insert` | ver matriz |
| `backend/app/system_monitor/sources.py:55` / `workers` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/sources.py:33` / `job_counts` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/sources.py:47` / `integrations` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/sources.py:70` / `database_waits` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/sources.py:91` / `collect_sections` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/system_monitor/sources.py:70` / `database_waits` | O | query/ORM | `text` | ver matriz |
| `backend/app/system_monitor/sources.py:55` / `workers` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/sources.py:88` / `collect_sections` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/sources.py:91` / `collect_sections` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/sources.py:33` / `job_counts` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/sources.py:47` / `integrations` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/sources.py:88` / `collect_sections` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/storage.py:25` / `file_inventory` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/storage.py:34` / `file_inventory` | O | gate | `media_namespace` | ver matriz |
| `backend/app/system_monitor/storage.py:37` / `file_inventory` | O | gate | `media_namespace` | ver matriz |
| `backend/app/system_monitor/storage.py:40` / `file_inventory` | O | query/ORM | `seen.add` | ver matriz |
| `backend/app/system_monitor/storage.py:21` / `file_inventory` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/storage.py:22` / `file_inventory` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/storage.py:23` / `file_inventory` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/store.py:111` / `prune` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:112` / `prune` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:25` / `bounded` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:26` / `bounded` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:43` / `save_buckets` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:87` / `http_history` | O | efeito potencial | `utc(minute).replace` | ver matriz |
| `backend/app/system_monitor/store.py:108` / `prune` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:24` / `bounded` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:25` / `bounded` | O | query/ORM | `text` | ver matriz |
| `backend/app/system_monitor/store.py:26` / `bounded` | O | query/ORM | `text` | ver matriz |
| `backend/app/system_monitor/store.py:51` / `operation_summary` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:79` / `http_history` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/system_monitor/store.py:24` / `bounded` | O | query/ORM | `text` | ver matriz |
| `backend/app/system_monitor/store.py:42` / `save_buckets` | O | query/ORM | `insert` | ver matriz |
| `backend/app/system_monitor/store.py:111` / `prune` | O | query/ORM | `delete` | ver matriz |
| `backend/app/system_monitor/store.py:112` / `prune` | O | query/ORM | `delete` | ver matriz |
| `backend/app/system_monitor/store.py:108` / `prune` | O | query/ORM | `delete` | ver matriz |
| `backend/app/system_monitor/store.py:107` / `prune` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/store.py:51` / `operation_summary` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/store.py:110` / `prune` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/store.py:79` / `http_history` | O | query/ORM | `select` | ver matriz |
| `backend/app/system_monitor/telemetry.py:28` / `record` | O | efeito potencial | `datetime.now(UTC).replace` | ver matriz |
| `backend/app/system_monitor/telemetry.py:57` / `heartbeat` | O | query/ORM | `_workers.get` | ver matriz |
| `backend/app/system_monitor/telemetry.py:126` / `finish` | O | query/ORM | `scope.get` | ver matriz |
| `backend/app/system_monitor/telemetry.py:138` / `observed_send` | O | efeito potencial | `send` | ver matriz |
| `backend/app/system_monitor/telemetry.py:139` / `observed_send` | O | query/ORM | `message.get` | ver matriz |
| `backend/app/system_monitor/telemetry.py:135` / `observed_send` | O | query/ORM | `scope.get` | ver matriz |
| `backend/app/system_monitor/telemetry.py:137` / `observed_send` | O | query/ORM | `message.get` | ver matriz |
| `backend/app/tenancy.py:30` / `require_admin_tenant` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/tenancy.py:40` / `require_admin_tenant` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:48` / `require_parent_tenant` | A | gate | `owned_record` | ver matriz |
| `backend/app/tenancy.py:56` / `bind_domain_owner` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:70` / `bind_financial_reconciliation` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenancy.py:73` / `bind_financial_reconciliation` | A | query/ORM | `db.info.setdefault('tenant_financial_reconciliation', set()).add` | ver matriz |
| `backend/app/tenancy.py:81` / `bind_privacy_retention` | A | query/ORM | `db.info.setdefault('tenant_privacy_retention', set()).add` | ver matriz |
| `backend/app/tenancy.py:94` / `_remember_changed_owners` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:17` / `require_single_tenant` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenancy.py:24` / `require_admin_tenant` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenancy.py:38` / `require_admin_tenant` | A | query/ORM | `db.info.setdefault('tenant_platform_identity', set()).add` | ver matriz |
| `backend/app/tenancy.py:57` / `bind_domain_owner` | A | query/ORM | `db.info.setdefault('tenant_domain_owners', set()).add` | ver matriz |
| `backend/app/tenancy.py:79` / `bind_privacy_retention` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/tenancy.py:88` / `domain_session` | A | gate | `enable_domain_guard` | ver matriz |
| `backend/app/tenancy.py:103` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:109` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:110` / `_revalidate_domain_commit` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenancy.py:114` / `_revalidate_domain_commit` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenancy.py:70` / `bind_financial_reconciliation` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:111` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:115` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:116` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:117` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:118` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:121` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:122` / `_revalidate_domain_commit` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenancy.py:110` / `_revalidate_domain_commit` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:114` / `_revalidate_domain_commit` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:17` / `require_single_tenant` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:24` / `require_admin_tenant` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:122` / `_revalidate_domain_commit` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:40` / `require_new_work` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:58` / `request_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:60` / `request_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:63` / `request_closure` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure.py:66` / `request_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:80` / `request_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:85` / `request_closure` | L | efeito potencial | `latest_published` | ver matriz |
| `backend/app/tenant_closure.py:88` / `request_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:96` / `request_closure` | L | produtor | `TenantClosureRequest` | ver matriz |
| `backend/app/tenant_closure.py:100` / `request_closure` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_closure.py:111` / `finalize_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:115` / `finalize_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:138` / `finalize_closure` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/tenant_closure.py:141` / `finalize_closure` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/tenant_closure.py:145` / `finalize_closure` | L | query/ORM | `db.info.setdefault('tenant_closure_transition', set()).add` | ver matriz |
| `backend/app/tenant_closure.py:92` / `request_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure.py:60` / `request_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:66` / `request_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:80` / `request_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:88` / `request_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:92` / `request_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:138` / `finalize_closure` | L | query/ORM | `update` | ver matriz |
| `backend/app/tenant_closure.py:141` / `finalize_closure` | L | query/ORM | `update` | ver matriz |
| `backend/app/tenant_closure.py:40` / `require_new_work` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:58` / `request_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:111` / `finalize_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure.py:115` / `finalize_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_api.py:101` / `<módulo>` | L | query/ORM | `router.get` | ver matriz |
| `backend/app/tenant_closure_api.py:61` / `_context` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_api.py:62` / `_context` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure_api.py:63` / `_context` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_api.py:103` / `closure_status` | L | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/tenant_closure_api.py:109` / `closure_status` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_api.py:118` / `closure_status` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_api.py:148` / `submit_closure` | L | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/tenant_closure_api.py:79` / `_terms_state` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_api.py:94` / `_public_blockers` | L | query/ORM | `_BLOCKER_MESSAGES.get` | ver matriz |
| `backend/app/tenant_closure_api.py:112` / `closure_status` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_api.py:61` / `_context` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_api.py:63` / `_context` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_api.py:109` / `closure_status` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_api.py:79` / `_terms_state` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_api.py:112` / `closure_status` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_api.py:118` / `closure_status` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:85` / `_public_response` | L | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/tenant_closure_identity.py:90` / `_same_host_origin` | L | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:127` / `_current_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:171` / `_matching_admin` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:176` / `_matching_admin` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:177` / `_matching_admin` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:184` / `_matching_admin` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:188` / `_matching_admin` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:198` / `_matching_admin` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:212` / `request_identity_verification` | L | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/tenant_closure_identity.py:224` / `request_identity_verification` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:262` / `request_identity_verification` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_identity.py:271` / `request_identity_verification` | L | produtor | `TenantClosureIdentityVerification` | ver matriz |
| `backend/app/tenant_closure_identity.py:288` / `request_identity_verification` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_closure_identity.py:321` / `confirm_identity_verification` | L | query/ORM | `response.headers.update` | ver matriz |
| `backend/app/tenant_closure_identity.py:330` / `confirm_identity_verification` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:338` / `confirm_identity_verification` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:384` / `confirm_identity_verification` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:388` / `confirm_identity_verification` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:389` / `confirm_identity_verification` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:394` / `confirm_identity_verification` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:399` / `confirm_identity_verification` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:403` / `confirm_identity_verification` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_identity.py:155` / `cleanup_expired_identity_challenges` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_identity.py:218` / `request_identity_verification` | L | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:290` / `request_identity_verification` | L | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/tenant_closure_identity.py:326` / `confirm_identity_verification` | L | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:369` / `confirm_identity_verification` | L | efeito potencial | `decrypt_private_field` | ver matriz |
| `backend/app/tenant_closure_identity.py:193` / `_matching_admin` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:278` / `request_identity_verification` | L | efeito potencial | `encrypt_private_field` | ver matriz |
| `backend/app/tenant_closure_identity.py:281` / `request_identity_verification` | L | efeito potencial | `encrypt_private_field` | ver matriz |
| `backend/app/tenant_closure_identity.py:374` / `confirm_identity_verification` | L | efeito potencial | `decrypt_private_field` | ver matriz |
| `backend/app/tenant_closure_identity.py:171` / `_matching_admin` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:177` / `_matching_admin` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:188` / `_matching_admin` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:224` / `request_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:384` / `confirm_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:389` / `confirm_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:394` / `confirm_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:101` / `_same_host_origin` | L | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:184` / `_matching_admin` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:262` / `request_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:330` / `confirm_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:399` / `confirm_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:403` / `confirm_identity_verification` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:98` / `_same_host_origin` | L | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/tenant_closure_identity.py:155` / `cleanup_expired_identity_challenges` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_identity.py:128` / `_current_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_obligations.py:81` / `_evaluate` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure_obligations.py:42` / `_utc` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/tenant_closure_obligations.py:46` / `_exists` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_obligations.py:54` / `operational_obligation_blockers` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:57` / `operational_obligation_blockers` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:60` / `operational_obligation_blockers` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:62` / `operational_obligation_blockers` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:85` / `_evaluate` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_obligations.py:96` / `_evaluate` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_obligations.py:135` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:137` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:140` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:75` / `operational_obligation_blockers` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:100` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:110` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:93` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:103` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:129` / `_evaluate` | L | query/ORM | `covered_sources.update` | ver matriz |
| `backend/app/tenant_closure_obligations.py:133` / `_evaluate` | L | query/ORM | `covered_sources.update` | ver matriz |
| `backend/app/tenant_closure_obligations.py:139` / `_evaluate` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_obligations.py:85` / `_evaluate` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_obligations.py:95` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:115` / `_evaluate` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_obligations.py:131` / `_evaluate` | L | query/ORM | `reasons.add` | ver matriz |
| `backend/app/tenant_closure_obligations.py:133` / `_evaluate` | L | query/ORM | `item.get` | ver matriz |
| `backend/app/tenant_closure_obligations.py:133` / `_evaluate` | L | query/ORM | `cycle.manifest.get` | ver matriz |
| `backend/app/tenant_closure_obligations.py:139` / `_evaluate` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_obligations.py:115` / `_evaluate` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_obligations.py:46` / `_exists` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_obligations.py:96` / `_evaluate` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:34` / `bind_account_recovery` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure_recovery.py:37` / `bind_account_recovery` | L | query/ORM | `db.info.setdefault('tenant_archive_recovery', set()).add` | ver matriz |
| `backend/app/tenant_closure_recovery.py:63` / `archive_execution_authorized` | L | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenant_closure_recovery.py:68` / `bind_operation_recovery` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:75` / `bind_operation_recovery` | L | query/ORM | `db.info.setdefault('tenant_archive_recovery', set()).add` | ver matriz |
| `backend/app/tenant_closure_recovery.py:104` / `closure_console_payload` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_closure_recovery.py:109` / `closure_console_payload` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:189` / `require_batch` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:203` / `request_batch` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:206` / `request_batch` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:212` / `request_batch` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:237` / `request_batch` | L | produtor | `TenantClosureRecoveryBatch` | ver matriz |
| `backend/app/tenant_closure_recovery.py:240` / `request_batch` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_closure_recovery.py:260` / `_ten_year_anniversary` | L | efeito potencial | `instant.replace` | ver matriz |
| `backend/app/tenant_closure_recovery.py:314` / `reopen_account` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:319` / `reopen_account` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:329` / `reopen_account` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:347` / `reopen_account` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_closure_recovery.py:99` / `_as_utc` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/tenant_closure_recovery.py:217` / `request_batch` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:222` / `request_batch` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:227` / `request_batch` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_recovery.py:248` / `request_batch` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_closure_recovery.py:257` / `_ten_year_anniversary` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/tenant_closure_recovery.py:264` / `_complete_recovery_set` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:270` / `_complete_recovery_set` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_recovery.py:285` / `_complete_recovery_set` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_closure_recovery.py:347` / `reopen_account` | L | produtor | `PlatformAdminEvent` | ver matriz |
| `backend/app/tenant_closure_recovery.py:41` / `_execution_proven` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/tenant_closure_recovery.py:80` / `batch_payload` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/tenant_closure_recovery.py:134` / `closure_console_payload` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_closure_recovery.py:148` / `closure_console_payload` | L | query/ORM | `media_deletion.get` | ver matriz |
| `backend/app/tenant_closure_recovery.py:248` / `request_batch` | L | produtor | `TenantClosureRecoveryItem` | ver matriz |
| `backend/app/tenant_closure_recovery.py:68` / `bind_operation_recovery` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:189` / `require_batch` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:206` / `request_batch` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:319` / `reopen_account` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:149` / `closure_console_payload` | L | query/ORM | `deletion_batch.get` | ver matriz |
| `backend/app/tenant_closure_recovery.py:217` / `request_batch` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:222` / `request_batch` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:227` / `request_batch` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:264` / `_complete_recovery_set` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:270` / `_complete_recovery_set` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:109` / `closure_console_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:203` / `request_batch` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:212` / `request_batch` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:314` / `reopen_account` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:80` / `batch_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:134` / `closure_console_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:329` / `reopen_account` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:285` / `_complete_recovery_set` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_closure_recovery.py:41` / `_execution_proven` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_hosts.py:66` / `tenant_for_host` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_hosts.py:87` / `closed_tenant_for_host` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_hosts.py:75` / `tenant_for_host` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_hosts.py:125` / `canonical_host_for_tenant` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_hosts.py:66` / `tenant_for_host` | X | query/ORM | `select` | ver matriz |
| `backend/app/tenant_hosts.py:75` / `tenant_for_host` | X | query/ORM | `select` | ver matriz |
| `backend/app/tenant_hosts.py:88` / `closed_tenant_for_host` | X | query/ORM | `select` | ver matriz |
| `backend/app/tenant_hosts.py:125` / `canonical_host_for_tenant` | X | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:55` / `_latest_closure` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:126` / `evaluate_media_deletion_preflight` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_media_deletion.py:244` / `media_deletion_console_payload` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_media_deletion.py:382` / `request_media_deletion` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:387` / `request_media_deletion` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:402` / `request_media_deletion` | L | produtor | `TenantClosureMediaDeletionBatch` | ver matriz |
| `backend/app/tenant_media_deletion.py:417` / `request_media_deletion` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_media_deletion.py:463` / `retry_media_deletion` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:468` / `retry_media_deletion` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:475` / `retry_media_deletion` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:50` / `_utc` | L | efeito potencial | `value.replace` | ver matriz |
| `backend/app/tenant_media_deletion.py:94` / `validate_cycle_catalog_for_deletion` | L | query/ORM | `by_id.get` | ver matriz |
| `backend/app/tenant_media_deletion.py:128` / `evaluate_media_deletion_preflight` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_media_deletion.py:251` / `media_deletion_console_payload` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:328` / `batch_inventory_snapshot` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_media_deletion.py:344` / `batch_inventory_snapshot` | L | query/ORM | `cycle_ids.add` | ver matriz |
| `backend/app/tenant_media_deletion.py:345` / `batch_inventory_snapshot` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_media_deletion.py:420` / `request_media_deletion` | L | produtor | `MediaArchiveOperation` | ver matriz |
| `backend/app/tenant_media_deletion.py:432` / `request_media_deletion` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_media_deletion.py:434` / `request_media_deletion` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/tenant_media_deletion.py:481` / `retry_media_deletion` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_media_deletion.py:502` / `retry_media_deletion` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:170` / `evaluate_media_deletion_preflight` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:434` / `request_media_deletion` | L | produtor | `TenantClosureMediaDeletionItem` | ver matriz |
| `backend/app/tenant_media_deletion.py:192` / `evaluate_media_deletion_preflight` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenant_media_deletion.py:209` / `evaluate_media_deletion_preflight` | L | query/ORM | `remote_ids.add` | ver matriz |
| `backend/app/tenant_media_deletion.py:256` / `media_deletion_console_payload` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/tenant_media_deletion.py:387` / `request_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:185` / `evaluate_media_deletion_preflight` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/tenant_media_deletion.py:186` / `evaluate_media_deletion_preflight` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/tenant_media_deletion.py:187` / `evaluate_media_deletion_preflight` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/tenant_media_deletion.py:188` / `evaluate_media_deletion_preflight` | L | query/ORM | `details.get` | ver matriz |
| `backend/app/tenant_media_deletion.py:251` / `media_deletion_console_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:147` / `evaluate_media_deletion_preflight` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:463` / `retry_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:475` / `retry_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:129` / `evaluate_media_deletion_preflight` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:152` / `evaluate_media_deletion_preflight` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_media_deletion.py:284` / `media_deletion_console_payload` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/tenant_media_deletion.py:345` / `batch_inventory_snapshot` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:502` / `retry_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:56` / `_latest_closure` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:382` / `request_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:468` / `retry_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:193` / `evaluate_media_deletion_preflight` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:329` / `batch_inventory_snapshot` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:482` / `retry_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:171` / `evaluate_media_deletion_preflight` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:284` / `media_deletion_console_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:147` / `evaluate_media_deletion_preflight` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:257` / `media_deletion_console_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_media_deletion.py:152` / `evaluate_media_deletion_preflight` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:38` / `_verified_media_deletion` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_profile_retention.py:60` / `profile_reduction_plan` | L | query/ORM | `db.get` | ver matriz |
| `backend/app/tenant_profile_retention.py:61` / `profile_reduction_plan` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_profile_retention.py:64` / `profile_reduction_plan` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_profile_retention.py:98` / `profile_retention_payload` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_profile_retention.py:116` / `reduce_closed_profile` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_profile_retention.py:120` / `reduce_closed_profile` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenant_profile_retention.py:46` / `_verified_media_deletion` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/tenant_profile_retention.py:38` / `_verified_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:46` / `_verified_media_deletion` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:64` / `profile_reduction_plan` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:61` / `profile_reduction_plan` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:98` / `profile_retention_payload` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:116` / `reduce_closed_profile` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:120` / `reduce_closed_profile` | L | query/ORM | `select` | ver matriz |
| `backend/app/tenant_profile_retention.py:86` / `profile_reduction_plan` | L | efeito potencial | `decrypt_private_field` | ver matriz |
| `backend/app/totp_crypto.py:32` / `legacy_totp_dual_write_enabled` | A | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/totp_crypto.py:110` / `encrypt` | A | efeito potencial | `AESGCM(self._keys[self.active_key_id]).encrypt` | ver matriz |
| `backend/app/totp_crypto.py:150` / `rotate` | A | efeito potencial | `self.decrypt` | ver matriz |
| `backend/app/totp_crypto.py:153` / `rotate` | A | efeito potencial | `self.encrypt` | ver matriz |
| `backend/app/totp_crypto.py:139` / `decrypt` | A | efeito potencial | `AESGCM(self._keys[key_id]).decrypt` | ver matriz |
| `backend/app/totp_crypto.py:76` / `from_environment` | A | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/totp_migration.py:16` / `_lock_admin_totp_table` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:42` / `encrypt_existing_totp` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:73` / `restore_legacy_totp` | A | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/totp_migration.py:78` / `restore_legacy_totp` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:104` / `contract_legacy_totp` | A | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/totp_migration.py:112` / `contract_legacy_totp` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:120` / `contract_legacy_totp` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:151` / `rotate_admin_totp_envelopes` | A | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/totp_migration.py:16` / `_lock_admin_totp_table` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:21` / `encrypt_existing_totp` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:31` / `encrypt_existing_totp` | A | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/totp_migration.py:43` / `encrypt_existing_totp` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:55` / `restore_legacy_totp` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:79` / `restore_legacy_totp` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:92` / `contract_legacy_totp` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:113` / `contract_legacy_totp` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:121` / `contract_legacy_totp` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:134` / `rotate_admin_totp_envelopes` | A | query/ORM | `select` | ver matriz |
| `backend/app/totp_migration.py:142` / `rotate_admin_totp_envelopes` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:152` / `rotate_admin_totp_envelopes` | A | query/ORM | `counts.get` | ver matriz |
| `backend/app/totp_migration.py:159` / `rotate_admin_totp_envelopes` | A | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/totp_migration.py:167` / `rotate_admin_totp_envelopes` | A | query/ORM | `connection.execute` | ver matriz |
| `backend/app/totp_migration.py:21` / `encrypt_existing_totp` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:40` / `encrypt_existing_totp` | A | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/totp_migration.py:55` / `restore_legacy_totp` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:92` / `contract_legacy_totp` | A | query/ORM | `text` | ver matriz |
| `backend/app/totp_migration.py:109` / `contract_legacy_totp` | A | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/totp_migration.py:168` / `rotate_admin_totp_envelopes` | A | query/ORM | `table.update` | ver matriz |
| `backend/app/totp_recovery.py:20` / `create_recovery_codes` | A | query/ORM | `selectors.add` | ver matriz |
| `backend/app/unified_checkout.py:58` / `communications_for_orders` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/unified_checkout.py:64` / `communications_for_orders` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:87` / `_materials` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:139` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:177` / `cart_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:331` / `_valid_materials` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:377` / `prepare_group` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:379` / `prepare_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:388` / `prepare_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:440` / `prepare_group` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/unified_checkout.py:483` / `payment_scopes` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/unified_checkout.py:490` / `payment_scopes` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:508` / `payment_scope` | S | query/ORM | `payment_scopes(db, {communication.payment_group_id}, tenant_id=communication.tenant_id).get` | ver matriz |
| `backend/app/unified_checkout.py:512` / `lock_payment_scope` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:515` / `lock_payment_scope` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:548` / `report_group` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:550` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:551` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:558` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:612` / `report_group` | S | produtor | `PaymentCommunication` | ver matriz |
| `backend/app/unified_checkout.py:618` / `report_group` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/unified_checkout.py:629` / `finalize_selection` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:631` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:632` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:636` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:661` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:675` / `finalize_selection` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/unified_checkout.py:679` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:104` / `existing_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:107` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:116` / `_materials` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:133` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:143` / `_materials` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:254` / `cart_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:410` / `prepare_group` | S | produtor | `PaymentGroup` | ver matriz |
| `backend/app/unified_checkout.py:425` / `prepare_group` | S | query/ORM | `drafts.get` | ver matriz |
| `backend/app/unified_checkout.py:477` / `group_payload` | S | query/ORM | `group.pix_configuration_snapshot.get` | ver matriz |
| `backend/app/unified_checkout.py:522` / `lock_payment_scope` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:529` / `lock_payment_scope` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:575` / `report_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:608` / `report_group` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:670` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:671` / `finalize_selection` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/unified_checkout.py:183` / `cart_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:219` / `cart_payload` | S | query/ORM | `folders.get` | ver matriz |
| `backend/app/unified_checkout.py:395` / `prepare_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:448` / `prepare_group` | S | query/ORM | `drafts.get` | ver matriz |
| `backend/app/unified_checkout.py:448` / `prepare_group` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/unified_checkout.py:488` / `payment_scopes` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:596` / `report_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:674` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:91` / `existing_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:641` / `finalize_selection` | S | query/ORM | `(existing.price_rule_snapshot or {}).get` | ver matriz |
| `backend/app/unified_checkout.py:673` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:208` / `cart_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:65` / `communications_for_orders` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:184` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:488` / `payment_scopes` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:491` / `payment_scopes` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:515` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:559` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:636` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:679` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:108` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:134` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:231` / `cart_payload` | S | query/ORM | `selection_created_at_by_photo.get` | ver matriz |
| `backend/app/unified_checkout.py:255` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:523` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:609` / `report_group` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:670` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:139` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:379` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:389` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:396` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:550` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:552` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:597` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:631` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:661` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:674` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:673` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:209` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:632` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:530` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:576` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:634` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/web_push.py:30` / `push_configuration_ready` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:31` / `push_configuration_ready` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:32` / `push_configuration_ready` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:134` / `send_push` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:135` / `send_push` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:143` / `send_push` | N | efeito potencial | `payload['id'].replace` | ver matriz |
| `backend/app/whatsapp_binding.py:73` / `resolve_binding` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/whatsapp_binding.py:98` / `resolve_binding` | N | query/ORM | `aliases.get` | ver matriz |
| `backend/app/whatsapp_binding.py:199` / `provider_for` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:209` / `photographer_phone` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:210` / `photographer_phone` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_binding.py:221` / `webhook_owner` | N | query/ORM | `payload.get` | ver matriz |
| `backend/app/whatsapp_binding.py:85` / `resolve_binding` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_binding.py:178` / `send_transactional` | N | efeito potencial | `self.adapter.send_transactional` | ver matriz |
| `backend/app/whatsapp_binding.py:225` / `webhook_owner` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/whatsapp_binding.py:103` / `resolve_binding` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_binding.py:238` / `webhook_owner` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:173` / `validate` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:85` / `resolve_binding` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_binding.py:114` / `resolve_binding` | N | gate | `require_single_tenant` | ver matriz |
| `backend/app/whatsapp_binding.py:225` / `webhook_owner` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_binding.py:232` / `webhook_owner` | N | gate | `require_single_tenant` | ver matriz |
| `backend/app/whatsapp_binding.py:103` / `resolve_binding` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_binding.py:210` / `photographer_phone` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_channel.py:56` / `channel_settings` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/whatsapp_channel.py:58` / `channel_settings` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_channel.py:91` / `channel_settings` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/whatsapp_channel.py:92` / `channel_settings` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_channel.py:142` / `notification_channel_ready` | N | gate | `provider_for` | ver matriz |
| `backend/app/whatsapp_channel.py:211` / `channel_payload` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_channel.py:59` / `channel_settings` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_channel.py:66` / `channel_settings` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_channel.py:85` / `channel_settings` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/whatsapp_channel.py:87` / `channel_settings` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_channel.py:85` / `channel_settings` | N | produtor | `WhatsAppChannelSettings` | ver matriz |
| `backend/app/whatsapp_channel.py:92` / `channel_settings` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_channel.py:87` / `channel_settings` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_delivery.py:59` / `encrypt_otp` | N | efeito potencial | `AESGCM(key).encrypt` | ver matriz |
| `backend/app/whatsapp_delivery.py:66` / `decrypt_otp` | N | efeito potencial | `AESGCM(key).decrypt(raw[:12], raw[12:], context.encode('utf-8')).decode` | ver matriz |
| `backend/app/whatsapp_delivery.py:66` / `decrypt_otp` | N | efeito potencial | `AESGCM(key).decrypt` | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py:59` / `credential_for_tenant` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py:73` / `provider_for_credential` | N | efeito potencial | `_cipher().decrypt` | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py:100` / `provision_tenant_credential` | N | efeito potencial | `cipher.encrypt(webhook_secret, tenant_id=tenant_id, credential_id=credential_id).payload` | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py:103` / `provision_tenant_credential` | N | produtor | `WhatsAppTenantCredential` | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py:59` / `credential_for_tenant` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py:100` / `provision_tenant_credential` | N | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/whatsapp_tenant_credentials.py:112` / `provision_tenant_credential` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/whatsapp_webhook.py:29` / `normalized_event` | N | efeito potencial | `str(value or '').strip().lower().replace` | ver matriz |
| `backend/app/whatsapp_webhook.py:38` / `_message_data` | N | query/ORM | `payload.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:68` / `process_whatsapp_webhook` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/whatsapp_webhook.py:70` / `process_whatsapp_webhook` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_webhook.py:80` / `process_whatsapp_webhook` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/whatsapp_webhook.py:137` / `process_whatsapp_webhook` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/whatsapp_webhook.py:45` / `_external_message_id` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:46` / `_external_message_id` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:47` / `_external_message_id` | N | query/ORM | `key.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:47` / `_external_message_id` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:47` / `_external_message_id` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:47` / `_external_message_id` | N | query/ORM | `update.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:52` / `_delivery_state` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:77` / `process_whatsapp_webhook` | N | query/ORM | `payload.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:81` / `process_whatsapp_webhook` | N | produtor | `WhatsAppWebhookReceipt` | ver matriz |
| `backend/app/whatsapp_webhook.py:89` / `process_whatsapp_webhook` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_webhook.py:45` / `_external_message_id` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:46` / `_external_message_id` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:52` / `_delivery_state` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:97` / `process_whatsapp_webhook` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/whatsapp_webhook.py:110` / `process_whatsapp_webhook` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_webhook.py:71` / `process_whatsapp_webhook` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_webhook.py:53` / `_delivery_state` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:53` / `_delivery_state` | N | query/ORM | `update.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:90` / `process_whatsapp_webhook` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_webhook.py:100` / `process_whatsapp_webhook` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:102` / `process_whatsapp_webhook` | N | query/ORM | `data.get('update', {}).get` | ver matriz |
| `backend/app/whatsapp_webhook.py:111` / `process_whatsapp_webhook` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_webhook.py:119` / `process_whatsapp_webhook` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:119` / `process_whatsapp_webhook` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:103` / `process_whatsapp_webhook` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:102` / `process_whatsapp_webhook` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:117` / `process_whatsapp_webhook` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/whatsapp_webhook.py:117` / `process_whatsapp_webhook` | N | query/ORM | `data.get` | ver matriz |
| `backend/app/worker.py:201` / `payment_notification_message` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:202` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:243` / `materialize_payment_delivery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:244` / `materialize_payment_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:249` / `materialize_payment_delivery` | X | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/worker.py:262` / `materialize_payment_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:274` / `mirror_payment_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:331` / `delivery_message` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:360` / `_record_attempt` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:927` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:169` / `process_next_media_archive_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:203` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:204` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:205` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:206` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:227` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:296` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:345` / `delivery_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:361` / `_record_attempt` | X | produtor | `WhatsAppDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:391` / `process_next_media_job` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:413` / `process_next_media_job` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:414` / `process_next_media_job` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:513` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:536` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:551` / `process_next_whatsapp_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:570` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:656` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:657` / `validate_email_origin` | X | query/ORM | `{'password_recovery': 'password_reset', 'email_verification': 'verify_admin_email'}.get` | ver matriz |
| `backend/app/worker.py:723` / `process_next_email_delivery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:741` / `process_next_email_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:751` / `process_next_email_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:767` / `process_next_email_delivery` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:852` / `materialize_next_payment_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:865` / `materialize_next_payment_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:930` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:932` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:941` / `process_next_gallery_reopening_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:977` / `reconcile_next_unknown_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:989` / `reconcile_next_unknown_delivery` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:1018` / `process_next_tenant_closure` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:1046` / `run_cycle` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:1121` / `process_asset_file_cleanup` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:1187` / `process_admin_security_cleanup` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:152` / `process_next_media_archive_operation` | X | efeito potencial | `enqueue_due_archive_window_notices` | ver matriz |
| `backend/app/worker.py:153` / `process_next_media_archive_operation` | X | efeito potencial | `enqueue_eligible_archive_operations` | ver matriz |
| `backend/app/worker.py:301` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:305` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:309` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:379` / `process_next_media_job` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:583` / `process_next_whatsapp_delivery` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:586` / `process_next_whatsapp_delivery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:587` / `process_next_whatsapp_delivery` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:658` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:781` / `process_next_email_delivery` | X | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/worker.py:787` / `process_next_email_delivery` | X | efeito potencial | `active_provider.send` | ver matriz |
| `backend/app/worker.py:799` / `process_next_email_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:901` / `send` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:909` / `send` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:915` / `send` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:928` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:953` / `process_next_gallery_reopening_notification` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:959` / `process_next_gallery_reopening_notification` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:1163` / `process_otp_privacy_cleanup` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:1192` / `process_admin_security_cleanup` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:245` / `materialize_payment_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:274` / `mirror_payment_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:315` / `validate_otp_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:321` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:338` / `delivery_message` | X | efeito potencial | `decrypt_otp` | ver matriz |
| `backend/app/worker.py:427` / `process_next_media_job` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:433` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:435` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:437` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:612` / `process_next_whatsapp_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:800` / `process_next_email_delivery` | X | produtor | `EmailDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:838` / `process_next_email_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:1195` / `process_admin_security_cleanup` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:169` / `process_next_media_archive_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:570` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:669` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:677` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:724` / `process_next_email_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:839` / `process_next_email_delivery` | X | produtor | `EmailDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:866` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:1022` / `process_next_tenant_closure` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:1025` / `process_next_tenant_closure` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:338` / `delivery_message` | X | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/worker.py:691` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:1019` / `process_next_tenant_closure` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:1163` / `process_otp_privacy_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:1192` / `process_admin_security_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:316` / `validate_otp_origin` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/worker.py:428` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:692` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:693` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:514` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:552` / `process_next_whatsapp_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:612` / `process_next_whatsapp_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:710` / `validate_email_origin` | X | query/ORM | `payload.get` | ver matriz |
| `backend/app/worker.py:752` / `process_next_email_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:742` / `process_next_email_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:537` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:853` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:941` / `process_next_gallery_reopening_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:978` / `reconcile_next_unknown_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:379` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:395` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:855` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:1121` / `process_asset_file_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:392` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `scripts/app_env_transition_inventory.py:429` / `binding_mismatches` | T | query/ORM | `services.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:587` / `collect` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:607` / `collect` | T | query/ORM | `probe.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:610` / `collect` | T | query/ORM | `probe.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:611` / `collect` | T | query/ORM | `probe.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:632` / `collect` | T | query/ORM | `probe.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:634` / `collect` | T | query/ORM | `whatsapp_bindings.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:636` / `collect` | T | query/ORM | `services.get('worker', {}).get` | ver matriz |
| `scripts/app_env_transition_inventory.py:184` / `env_map` | T | query/ORM | `(container.get('Config') or {}).get` | ver matriz |
| `scripts/app_env_transition_inventory.py:196` / `host_bindings` | T | query/ORM | `(container.get('NetworkSettings') or {}).get` | ver matriz |
| `scripts/app_env_transition_inventory.py:233` / `active_containers` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:239` / `active_containers` | T | query/ORM | `container.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:241` / `active_containers` | T | query/ORM | `container.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:242` / `active_containers` | T | query/ORM | `env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:249` / `active_containers` | T | query/ORM | `state.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:250` / `active_containers` | T | query/ORM | `(state.get('Health') or {}).get` | ver matriz |
| `scripts/app_env_transition_inventory.py:473` / `binding_mismatches` | T | query/ORM | `services.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:485` / `live_payment_gate` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:486` / `live_payment_gate` | T | query/ORM | `worker_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:512` / `compose_digest` | T | query/ORM | `service.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:597` / `collect` | T | query/ORM | `env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:614` / `collect` | T | query/ORM | `probe.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:650` / `collect` | T | query/ORM | `final_services.get('worker', {}).get` | ver matriz |
| `scripts/app_env_transition_inventory.py:204` / `host_bindings` | T | query/ORM | `binding.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:205` / `host_bindings` | T | query/ORM | `binding.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:230` / `active_containers` | T | query/ORM | `container.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:231` / `active_containers` | T | query/ORM | `config.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:238` / `active_containers` | T | query/ORM | `container.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:255` / `active_containers` | T | query/ORM | `container.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:264` / `active_containers` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:433` / `binding_mismatches` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:433` / `binding_mismatches` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:525` / `compose_digest` | T | query/ORM | `paths.add` | ver matriz |
| `scripts/app_env_transition_inventory.py:636` / `collect` | T | query/ORM | `services.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:671` / `collect` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:232` / `active_containers` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:420` / `verify_keyring` | T | query/ORM | `values.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:421` / `verify_keyring` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:422` / `verify_keyring` | T | query/ORM | `worker_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:602` / `collect` | T | query/ORM | `revisions.add` | ver matriz |
| `scripts/app_env_transition_inventory.py:650` / `collect` | T | query/ORM | `final_services.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:184` / `env_map` | T | query/ORM | `container.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:196` / `host_bindings` | T | query/ORM | `container.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:250` / `active_containers` | T | query/ORM | `state.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:435` / `binding_mismatches` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:435` / `binding_mismatches` | T | query/ORM | `worker_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:478` / `binding_mismatches` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:478` / `binding_mismatches` | T | query/ORM | `env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:551` / `integration_evidence` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:593` / `collect` | T | query/ORM | `env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:593` / `collect` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:540` / `provider_state` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:558` / `integration_evidence` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:566` / `integration_evidence` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory.py:574` / `integration_evidence` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/app_env_transition_inventory_report.py:10` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/app_env_transition_inventory_report.py:144` / `main` | T | efeito potencial | `output_path.write_text` | ver matriz |
| `scripts/app_env_transition_inventory_report.py:145` / `main` | T | efeito potencial | `summary_path.open` | ver matriz |
| `scripts/assert_homolog_schema_head.py:30` / `migration_heads` | T | query/ORM | `values.get` | ver matriz |
| `scripts/assert_homolog_schema_head.py:35` / `migration_heads` | T | query/ORM | `values.get` | ver matriz |
| `scripts/backend_ci.py:81` / `run_suite` | T | efeito potencial | `output.unlink` | ver matriz |
| `scripts/backend_ci.py:103` / `run_suite` | T | efeito potencial | `output.write_text` | ver matriz |
| `scripts/backend_ci.py:51` / `verify` | T | query/ORM | `report.get` | ver matriz |
| `scripts/backend_ci.py:54` / `verify` | T | query/ORM | `reports[0].get` | ver matriz |
| `scripts/backend_ci.py:62` / `verify` | T | query/ORM | `report.get` | ver matriz |
| `scripts/backend_ci.py:64` / `verify` | T | query/ORM | `report.get` | ver matriz |
| `scripts/backend_ci.py:96` / `pytest_collection_modifyitems` | T | query/ORM | `report.update` | ver matriz |
| `scripts/backend_ci.py:58` / `verify` | T | query/ORM | `report.get` | ver matriz |
| `scripts/backend_ci.py:58` / `verify` | T | query/ORM | `report.get` | ver matriz |
| `scripts/backend_ci.py:59` / `verify` | T | query/ORM | `report.get` | ver matriz |
| `scripts/backend_ci.py:119` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/backend_ci.py:60` / `verify` | T | query/ORM | `report.get` | ver matriz |
| `scripts/build_python_security_candidates.py:129` / `main` | T | efeito potencial | `args.output.write_text` | ver matriz |
| `scripts/build_python_security_candidates.py:118` / `main` | T | query/ORM | `info.update` | ver matriz |
| `scripts/build_python_security_candidates.py:67` / `imported_baseline` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/build_python_security_candidates.py:110` / `main` | T | efeito potencial | `Path(folder, 'approved-requirements-push.txt').write_bytes` | ver matriz |
| `scripts/build_python_security_candidates.py:111` / `main` | T | efeito potencial | `Path(folder, 'Dockerfile').write_text` | ver matriz |
| `scripts/build_python_security_candidates.py:77` / `imported_baseline` | T | query/ORM | `hashes.get` | ver matriz |
| `scripts/check_ci_results.py:12` / `validate_results` | T | query/ORM | `values.get` | ver matriz |
| `scripts/check_ci_results.py:21` / `validate_results` | T | query/ORM | `values.get` | ver matriz |
| `scripts/check_ci_results.py:22` / `validate_results` | T | query/ORM | `values.get` | ver matriz |
| `scripts/check_ci_results.py:31` / `validate_results` | T | query/ORM | `values.get` | ver matriz |
| `scripts/check_prod_app_release_scope.py:130` / `evaluate` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/check_prod_app_release_scope.py:121` / `evaluate` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:79` / `evaluate_maintenance` | T | query/ORM | `payload.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:84` / `evaluate_maintenance` | T | query/ORM | `maintenance.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:85` / `evaluate_maintenance` | T | query/ORM | `maintenance.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:90` / `evaluate_maintenance` | T | query/ORM | `maintenance.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:131` / `activation_status` | T | query/ORM | `payload.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:158` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:82` / `evaluate_maintenance` | T | query/ORM | `maintenance.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:99` / `evaluate_maintenance` | T | query/ORM | `app_manifest.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:80` / `evaluate_maintenance` | T | query/ORM | `maintenance.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:132` / `activation_status` | T | query/ORM | `payload.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:135` / `activation_status` | T | query/ORM | `gate.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:103` / `evaluate_maintenance` | T | query/ORM | `app_blobs.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:120` / `evaluate_maintenance` | T | query/ORM | `app_blobs.get` | ver matriz |
| `scripts/check_prod_facial_release_gates.py:136` / `activation_status` | T | query/ORM | `gate.get` | ver matriz |
| `scripts/classify_ci_scope.py:22` / `classify` | T | efeito potencial | `raw_path.replace` | ver matriz |
| `scripts/classify_prod_release.py:76` / `production_baseline_from_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/classify_prod_release.py:77` / `production_baseline_from_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/classify_prod_release.py:132` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/classify_prod_release.py:124` / `main` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/dependency_release.py:51` / `source` | T | efeito potencial | `git(root, 'show', '{}:{}'.format(revision, path)).replace` | ver matriz |
| `scripts/dependency_release.py:220` / `web_build` | T | query/ORM | `config.get('services', {}).get` | ver matriz |
| `scripts/dependency_release.py:221` / `web_build` | T | query/ORM | `service.get` | ver matriz |
| `scripts/dependency_release.py:242` / `plan` | T | query/ORM | `{'aarch64': 'arm64', 'x86_64': 'amd64'}.get` | ver matriz |
| `scripts/dependency_release.py:285` / `plan` | T | query/ORM | `report.update` | ver matriz |
| `scripts/dependency_release.py:151` / `required_inputs` | T | query/ORM | `required.add` | ver matriz |
| `scripts/dependency_release.py:226` / `web_build` | T | query/ORM | `service.get` | ver matriz |
| `scripts/dependency_release.py:226` / `web_build` | T | query/ORM | `service.get` | ver matriz |
| `scripts/dependency_release.py:226` / `web_build` | T | query/ORM | `service.get` | ver matriz |
| `scripts/dependency_release.py:240` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/dependency_release.py:242` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/dependency_release.py:279` / `plan` | T | query/ORM | `inventory.get('services', {}).get('api', {}).get` | ver matriz |
| `scripts/dependency_release.py:103` / `catalogue` | T | query/ORM | `services.setdefault(name, {}).update` | ver matriz |
| `scripts/dependency_release.py:117` / `copied_inputs` | T | efeito potencial | `dockerfile.replace` | ver matriz |
| `scripts/dependency_release.py:136` / `required_inputs` | T | efeito potencial | `body.replace` | ver matriz |
| `scripts/dependency_release.py:220` / `web_build` | T | query/ORM | `config.get` | ver matriz |
| `scripts/dependency_release.py:224` / `web_build` | T | query/ORM | `build.get` | ver matriz |
| `scripts/dependency_release.py:224` / `web_build` | T | query/ORM | `build.get` | ver matriz |
| `scripts/dependency_release.py:234` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/dependency_release.py:234` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/dependency_release.py:257` / `plan` | T | query/ORM | `inventory.get('services', {}).get` | ver matriz |
| `scripts/dependency_release.py:261` / `plan` | T | query/ORM | `current.get` | ver matriz |
| `scripts/dependency_release.py:262` / `plan` | T | query/ORM | `current.get` | ver matriz |
| `scripts/dependency_release.py:312` / `main` | T | query/ORM | `result.get` | ver matriz |
| `scripts/dependency_release.py:111` / `catalogue` | T | query/ORM | `build.get` | ver matriz |
| `scripts/dependency_release.py:169` / `impact` | T | query/ORM | `before.get` | ver matriz |
| `scripts/dependency_release.py:182` / `impact` | T | query/ORM | `before.get` | ver matriz |
| `scripts/dependency_release.py:269` / `plan` | T | query/ORM | `metadata.get` | ver matriz |
| `scripts/dependency_release.py:270` / `plan` | T | query/ORM | `current.get` | ver matriz |
| `scripts/dependency_release.py:275` / `plan` | T | query/ORM | `inventory.get('state', {}).get` | ver matriz |
| `scripts/dependency_release.py:276` / `plan` | T | query/ORM | `selected.get('web', {}).get` | ver matriz |
| `scripts/dependency_release.py:279` / `plan` | T | query/ORM | `inventory.get('services', {}).get` | ver matriz |
| `scripts/dependency_release.py:107` / `catalogue` | T | query/ORM | `build.get` | ver matriz |
| `scripts/dependency_release.py:254` / `plan` | T | query/ORM | `data.get` | ver matriz |
| `scripts/dependency_release.py:257` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/dependency_release.py:258` / `plan` | T | query/ORM | `current.get` | ver matriz |
| `scripts/dependency_release.py:263` / `plan` | T | query/ORM | `metadata.get` | ver matriz |
| `scripts/dependency_release.py:265` / `plan` | T | query/ORM | `metadata.get` | ver matriz |
| `scripts/dependency_release.py:265` / `plan` | T | query/ORM | `current.get` | ver matriz |
| `scripts/dependency_release.py:275` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/dependency_release.py:276` / `plan` | T | query/ORM | `selected.get` | ver matriz |
| `scripts/dependency_release.py:279` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/dependency_release.py:267` / `plan` | T | query/ORM | `current.get('packages', {}).get` | ver matriz |
| `scripts/dependency_release.py:170` / `impact` | T | query/ORM | `config.get` | ver matriz |
| `scripts/dependency_release.py:267` / `plan` | T | query/ORM | `current.get` | ver matriz |
| `scripts/environment_cutover_release.py:193` / `snapshot` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/environment_cutover_release.py:221` / `stores` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/environment_cutover_release.py:231` / `seal_config` | T | efeito potencial | `AESGCM(key).encrypt` | ver matriz |
| `scripts/environment_cutover_release.py:241` / `open_config` | T | efeito potencial | `AESGCM(saved.key).decrypt` | ver matriz |
| `scripts/environment_cutover_release.py:272` / `write_private` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/environment_cutover_release.py:444` / `configure_files` | T | query/ORM | `changes.update` | ver matriz |
| `scripts/environment_cutover_release.py:522` / `claim_release_marker` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/environment_cutover_release.py:544` / `clear_release_marker` | T | efeito potencial | `marker.unlink` | ver matriz |
| `scripts/environment_cutover_release.py:545` / `clear_release_marker` | T | efeito potencial | `sidecar.unlink` | ver matriz |
| `scripts/environment_cutover_release.py:108` / `environment` | T | query/ORM | `container['Config'].get` | ver matriz |
| `scripts/environment_cutover_release.py:135` / `canonical_mounts` | T | query/ORM | `item.get` | ver matriz |
| `scripts/environment_cutover_release.py:147` / `containers` | T | query/ORM | `item['Config']['Labels'].get` | ver matriz |
| `scripts/environment_cutover_release.py:234` / `seal_config` | T | efeito potencial | `base64.b64encode(encrypted).decode` | ver matriz |
| `scripts/environment_cutover_release.py:410` / `replace_file` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/environment_cutover_release.py:411` / `replace_file` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/environment_cutover_release.py:417` / `replace_file` | T | efeito potencial | `Path(filename).unlink` | ver matriz |
| `scripts/environment_cutover_release.py:516` / `load_receipt` | T | efeito potencial | `AESGCM(saved.key).decrypt` | ver matriz |
| `scripts/environment_cutover_release.py:730` / `recover_release` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/environment_cutover_release.py:761` / `main` | T | efeito potencial | `(STATE / 'production-release.lock').open` | ver matriz |
| `scripts/environment_cutover_release.py:95` / `verify_candidate` | T | query/ORM | `tree.get` | ver matriz |
| `scripts/environment_cutover_release.py:118` / `target_environment` | T | query/ORM | `source.get` | ver matriz |
| `scripts/environment_cutover_release.py:197` / `snapshot` | T | query/ORM | `probe.get` | ver matriz |
| `scripts/environment_cutover_release.py:265` / `compose_model` | T | efeito potencial | `v.replace` | ver matriz |
| `scripts/environment_cutover_release.py:396` / `replace_file` | T | efeito potencial | `path.open` | ver matriz |
| `scripts/environment_cutover_release.py:427` / `rewrite_environment` | T | query/ORM | `seen.add` | ver matriz |
| `scripts/environment_cutover_release.py:476` / `stop_consumers` | T | query/ORM | `runtime(config, 'idle', operation).get` | ver matriz |
| `scripts/environment_cutover_release.py:534` / `claim_release_marker` | T | efeito potencial | `path.unlink` | ver matriz |
| `scripts/environment_cutover_release.py:93` / `verify_candidate` | T | query/ORM | `latest.get` | ver matriz |
| `scripts/environment_cutover_release.py:93` / `verify_candidate` | T | query/ORM | `latest.get` | ver matriz |
| `scripts/environment_cutover_release.py:96` / `verify_candidate` | T | query/ORM | `x.get` | ver matriz |
| `scripts/environment_cutover_release.py:104` / `verify_candidate` | T | query/ORM | `expected.get` | ver matriz |
| `scripts/environment_cutover_release.py:173` / `snapshot` | T | query/ORM | `item['State'].get('Health', {}).get` | ver matriz |
| `scripts/environment_cutover_release.py:180` / `snapshot` | T | query/ORM | `environment(services[name]).get` | ver matriz |
| `scripts/environment_cutover_release.py:202` / `snapshot` | T | query/ORM | `environment(item).get` | ver matriz |
| `scripts/environment_cutover_release.py:290` / `maintenance_api` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/environment_cutover_release.py:291` / `maintenance_api` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/environment_cutover_release.py:339` / `runtime` | T | query/ORM | `result.get` | ver matriz |
| `scripts/environment_cutover_release.py:374` / `model_path` | T | efeito potencial | `v.replace` | ver matriz |
| `scripts/environment_cutover_release.py:442` / `configure_files` | T | query/ORM | `old.get` | ver matriz |
| `scripts/environment_cutover_release.py:558` / `verify_running` | T | query/ORM | `current['State'].get('Health', {}).get` | ver matriz |
| `scripts/environment_cutover_release.py:612` / `apply` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/environment_cutover_release.py:725` / `recover_release` | T | query/ORM | `runtime(config, 'idle', operation).get` | ver matriz |
| `scripts/environment_cutover_release.py:731` / `recover_release` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/environment_cutover_release.py:89` / `verify_candidate` | T | query/ORM | `r.get` | ver matriz |
| `scripts/environment_cutover_release.py:90` / `verify_candidate` | T | query/ORM | `r.get` | ver matriz |
| `scripts/environment_cutover_release.py:90` / `verify_candidate` | T | query/ORM | `r.get` | ver matriz |
| `scripts/environment_cutover_release.py:90` / `verify_candidate` | T | query/ORM | `r.get` | ver matriz |
| `scripts/environment_cutover_release.py:92` / `verify_candidate` | T | query/ORM | `r.get` | ver matriz |
| `scripts/environment_cutover_release.py:267` / `compose_model` | T | efeito potencial | `x.replace` | ver matriz |
| `scripts/environment_cutover_release.py:173` / `snapshot` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/environment_cutover_release.py:558` / `verify_running` | T | query/ORM | `current['State'].get` | ver matriz |
| `scripts/environment_cutover_release.py:174` / `snapshot` | T | query/ORM | `item['NetworkSettings'].get` | ver matriz |
| `scripts/environment_cutover_release.py:645` / `apply` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/environment_cutover_release.py:646` / `apply` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/face_benchmark.py:22` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/face_benchmark.py:347` / `<módulo>` | T | efeito potencial | `args.output.write_text` | ver matriz |
| `scripts/face_benchmark.py:119` / `load_corpus` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_benchmark.py:120` / `load_corpus` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_benchmark.py:176` / `benchmark` | T | query/ORM | `corpus_digest.update` | ver matriz |
| `scripts/face_benchmark.py:46` / `visit` | T | query/ORM | `seen.add` | ver matriz |
| `scripts/face_benchmark.py:117` / `load_corpus` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_benchmark.py:185` / `benchmark` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_benchmark.py:121` / `load_corpus` | T | query/ORM | `authorization.get` | ver matriz |
| `scripts/face_benchmark.py:121` / `load_corpus` | T | query/ORM | `authorization.get` | ver matriz |
| `scripts/face_benchmark.py:131` / `load_corpus` | T | query/ORM | `item.get` | ver matriz |
| `scripts/face_benchmark.py:143` / `load_corpus` | T | query/ORM | `face.get` | ver matriz |
| `scripts/face_benchmark.py:222` / `benchmark` | T | efeito potencial | `Image.open` | ver matriz |
| `scripts/face_spike/dataset.py:117` / `build_dataset` | T | efeito potencial | `(root / MARKER_NAME).write_text` | ver matriz |
| `scripts/face_spike/dataset.py:197` / `build_dataset` | T | efeito potencial | `manifest_path.write_text` | ver matriz |
| `scripts/face_spike/dataset.py:254` / `clean_dataset` | T | efeito potencial | `shutil.rmtree` | ver matriz |
| `scripts/face_spike/dataset.py:25` / `_sha256` | T | efeito potencial | `path.open` | ver matriz |
| `scripts/face_spike/dataset.py:119` / `build_dataset` | T | efeito potencial | `Image.open` | ver matriz |
| `scripts/face_spike/dataset.py:121` / `build_dataset` | T | efeito potencial | `Image.open` | ver matriz |
| `scripts/face_spike/dataset.py:173` / `build_dataset` | T | query/ORM | `entry.update` | ver matriz |
| `scripts/face_spike/dataset.py:185` / `build_dataset` | T | query/ORM | `entry.update` | ver matriz |
| `scripts/face_spike/dataset.py:193` / `build_dataset` | T | query/ORM | `entry.update` | ver matriz |
| `scripts/face_spike/dataset.py:222` / `verify_dataset` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_spike/dataset.py:27` / `_sha256` | T | query/ORM | `digest.update` | ver matriz |
| `scripts/face_spike/dataset.py:143` / `build_dataset` | T | query/ORM | `entry.update` | ver matriz |
| `scripts/face_spike/dataset.py:152` / `build_dataset` | T | query/ORM | `entry.update` | ver matriz |
| `scripts/face_spike/harness.py:96` / `load_dataset_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_spike/harness.py:387` / `main` | T | efeito potencial | `args.output.write_text` | ver matriz |
| `scripts/face_spike/harness.py:315` / `run_benchmark` | T | query/ORM | `query_states.get` | ver matriz |
| `scripts/face_spike/models.py:50` / `prepare_models` | T | efeito potencial | `marker_path.write_text` | ver matriz |
| `scripts/face_spike/models.py:117` / `clean_models` | T | efeito potencial | `shutil.rmtree` | ver matriz |
| `scripts/face_spike/models.py:19` / `_sha256` | T | efeito potencial | `path.open` | ver matriz |
| `scripts/face_spike/models.py:21` / `_sha256` | T | query/ORM | `digest.update` | ver matriz |
| `scripts/face_spike/models.py:34` / `load_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_spike/models.py:34` / `load_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/face_spike/models.py:46` / `prepare_models` | T | query/ORM | `marker.get` | ver matriz |
| `scripts/face_spike/models.py:72` / `prepare_models` | T | efeito potencial | `target.unlink` | ver matriz |
| `scripts/face_spike/models.py:66` / `prepare_models` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/face_spike/models.py:68` / `prepare_models` | T | efeito potencial | `partial.unlink` | ver matriz |
| `scripts/face_spike/models.py:63` / `prepare_models` | T | efeito potencial | `partial.open` | ver matriz |
| `scripts/face_spike/models.py:65` / `prepare_models` | T | efeito potencial | `shutil.copyfileobj` | ver matriz |
| `scripts/facial_runtime_candidate.py:72` / `_python_source_bytes` | T | efeito potencial | `data.replace` | ver matriz |
| `scripts/facial_runtime_candidate.py:95` / `_wheel` | T | efeito potencial | `name.replace` | ver matriz |
| `scripts/facial_runtime_candidate.py:247` / `prepare_context` | T | query/ORM | `baseline.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:258` / `prepare_context` | T | query/ORM | `runtime.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:259` / `prepare_context` | T | query/ORM | `SERVICE_OVERLAYS.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:269` / `prepare_context` | T | efeito potencial | `_file_bytes(manifest_path, limit=32768).replace` | ver matriz |
| `scripts/facial_runtime_candidate.py:277` / `prepare_context` | T | query/ORM | `donor.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:301` / `prepare_context` | T | query/ORM | `expected_modules.update` | ver matriz |
| `scripts/facial_runtime_candidate.py:303` / `prepare_context` | T | query/ORM | `expected_packages.update` | ver matriz |
| `scripts/facial_runtime_candidate.py:357` / `prepare_context` | T | efeito potencial | `(destination / 'Dockerfile').write_text` | ver matriz |
| `scripts/facial_runtime_candidate.py:358` / `prepare_context` | T | efeito potencial | `(destination / '.dockerignore').write_text` | ver matriz |
| `scripts/facial_runtime_candidate.py:240` / `prepare_context` | T | query/ORM | `baseline.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:240` / `prepare_context` | T | query/ORM | `donor.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:252` / `prepare_context` | T | query/ORM | `runtime.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:280` / `prepare_context` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:283` / `prepare_context` | T | query/ORM | `required_assets.add` | ver matriz |
| `scripts/facial_runtime_candidate.py:294` / `prepare_context` | T | query/ORM | `wheel_names.add` | ver matriz |
| `scripts/facial_runtime_candidate.py:318` / `prepare_context` | T | efeito potencial | `target.write_bytes` | ver matriz |
| `scripts/facial_runtime_candidate.py:322` / `prepare_context` | T | efeito potencial | `(destination / 'wheelhouse' / name).write_bytes` | ver matriz |
| `scripts/facial_runtime_candidate.py:328` / `prepare_context` | T | efeito potencial | `(destination / name).write_bytes` | ver matriz |
| `scripts/facial_runtime_candidate.py:330` / `prepare_context` | T | efeito potencial | `(destination / 'requirements-restore.txt').write_text` | ver matriz |
| `scripts/facial_runtime_candidate.py:54` / `_file_bytes` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_candidate.py:172` / `verify_context` | T | efeito potencial | `str(p.relative_to(plan.context)).replace` | ver matriz |
| `scripts/facial_runtime_candidate.py:248` / `prepare_context` | T | query/ORM | `runtime.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:250` / `prepare_context` | T | query/ORM | `donor.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:251` / `prepare_context` | T | query/ORM | `donor.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:272` / `prepare_context` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:273` / `prepare_context` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:275` / `prepare_context` | T | query/ORM | `donor.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:284` / `prepare_context` | T | query/ORM | `assets.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:287` / `prepare_context` | T | query/ORM | `assets['markina-face-models/.markina-face-models.json'].get` | ver matriz |
| `scripts/facial_runtime_candidate.py:194` / `inspect` | T | query/ORM | `info.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:194` / `inspect` | T | query/ORM | `info.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:195` / `inspect` | T | query/ORM | `info.get('Config', {}).get` | ver matriz |
| `scripts/facial_runtime_candidate.py:196` / `inspect` | T | query/ORM | `info.get('Config', {}).get` | ver matriz |
| `scripts/facial_runtime_candidate.py:249` / `prepare_context` | T | query/ORM | `runtime.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:255` / `prepare_context` | T | query/ORM | `package_versions.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:256` / `prepare_context` | T | query/ORM | `donor.get('installed_versions', {}).get` | ver matriz |
| `scripts/facial_runtime_candidate.py:274` / `prepare_context` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:288` / `prepare_context` | T | query/ORM | `assets['markina-face-models/.markina-face-models.json'].get` | ver matriz |
| `scripts/facial_runtime_candidate.py:360` / `prepare_context` | T | efeito potencial | `str(p.relative_to(destination)).replace` | ver matriz |
| `scripts/facial_runtime_candidate.py:111` / `_wheel` | T | efeito potencial | `metadata['Name'].replace` | ver matriz |
| `scripts/facial_runtime_candidate.py:192` / `inspect` | T | query/ORM | `info.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:195` / `inspect` | T | query/ORM | `info.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:196` / `inspect` | T | query/ORM | `info.get` | ver matriz |
| `scripts/facial_runtime_candidate.py:256` / `prepare_context` | T | query/ORM | `donor.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:85` / `validate` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:95` / `verify_inspect` | T | query/ORM | `observation.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:131` / `normalize_archive` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_image_import.py:134` / `normalize_archive` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/facial_runtime_image_import.py:144` / `read_json` | T | query/ORM | `by_name.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:157` / `normalize_archive` | T | query/ORM | `descriptor.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:164` / `normalize_archive` | T | query/ORM | `manifest.get('config', {}).get` | ver matriz |
| `scripts/facial_runtime_image_import.py:176` / `normalize_archive` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:184` / `normalize_archive` | T | query/ORM | `config.get('rootfs', {}).get` | ver matriz |
| `scripts/facial_runtime_image_import.py:185` / `normalize_archive` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:202` / `normalize_archive` | T | query/ORM | `existing_by_config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:235` / `normalize_archive` | T | query/ORM | `seen.add` | ver matriz |
| `scripts/facial_runtime_image_import.py:244` / `normalize_archive` | T | query/ORM | `descriptors_by_config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:252` / `normalize_archive` | T | query/ORM | `descriptor.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:256` / `normalize_archive` | T | query/ORM | `annotations.update` | ver matriz |
| `scripts/facial_runtime_image_import.py:77` / `validate` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:78` / `validate` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:79` / `validate` | T | query/ORM | `manifest.get('config', {}).get` | ver matriz |
| `scripts/facial_runtime_image_import.py:80` / `validate` | T | query/ORM | `manifest['config'].get` | ver matriz |
| `scripts/facial_runtime_image_import.py:82` / `validate` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:82` / `validate` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:83` / `validate` | T | query/ORM | `config.get('rootfs', {}).get` | ver matriz |
| `scripts/facial_runtime_image_import.py:88` / `validate` | T | query/ORM | `config['rootfs'].get` | ver matriz |
| `scripts/facial_runtime_image_import.py:98` / `verify_inspect` | T | query/ORM | `observation.get('Descriptor', {}).get` | ver matriz |
| `scripts/facial_runtime_image_import.py:100` / `verify_inspect` | T | query/ORM | `observation.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:101` / `verify_inspect` | T | query/ORM | `observation.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:102` / `verify_inspect` | T | query/ORM | `observation.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:102` / `verify_inspect` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:103` / `verify_inspect` | T | query/ORM | `observation.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:103` / `verify_inspect` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:104` / `verify_inspect` | T | query/ORM | `observation.get('RootFS', {}).get` | ver matriz |
| `scripts/facial_runtime_image_import.py:105` / `verify_inspect` | T | query/ORM | `observation['RootFS'].get` | ver matriz |
| `scripts/facial_runtime_image_import.py:168` / `normalize_archive` | T | efeito potencial | `config_id.replace` | ver matriz |
| `scripts/facial_runtime_image_import.py:194` / `normalize_archive` | T | query/ORM | `by_name.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:217` / `normalize_archive` | T | query/ORM | `by_name.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:270` / `normalize_archive` | T | query/ORM | `h.update` | ver matriz |
| `scripts/facial_runtime_image_import.py:274` / `normalize_archive` | T | query/ORM | `by_name.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:282` / `normalize_archive` | T | efeito potencial | `binding.local_image.replace` | ver matriz |
| `scripts/facial_runtime_image_import.py:287` / `normalize_archive` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_image_import.py:288` / `normalize_archive` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/facial_runtime_image_import.py:153` / `normalize_archive` | T | query/ORM | `index.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:153` / `normalize_archive` | T | query/ORM | `index.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:160` / `normalize_archive` | T | efeito potencial | `reference.replace` | ver matriz |
| `scripts/facial_runtime_image_import.py:164` / `normalize_archive` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:184` / `normalize_archive` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:216` / `normalize_archive` | T | efeito potencial | `manifest_id.replace` | ver matriz |
| `scripts/facial_runtime_image_import.py:250` / `normalize_archive` | T | query/ORM | `descriptor.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:79` / `validate` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:83` / `validate` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:98` / `verify_inspect` | T | query/ORM | `observation.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:104` / `verify_inspect` | T | query/ORM | `observation.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:158` / `normalize_archive` | T | query/ORM | `descriptor.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:161` / `normalize_archive` | T | query/ORM | `descriptor.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:274` / `normalize_archive` | T | efeito potencial | `layer['digest'].replace` | ver matriz |
| `scripts/facial_runtime_image_import.py:86` / `validate` | T | query/ORM | `x.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:87` / `validate` | T | query/ORM | `x.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:224` / `normalize_archive` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_image_import.py:225` / `normalize_archive` | T | efeito potencial | `x['digest'].replace` | ver matriz |
| `scripts/facial_runtime_image_import.py:226` / `normalize_archive` | T | query/ORM | `binding_manifest.get` | ver matriz |
| `scripts/facial_runtime_layer_probe.py:30` / `verify_export` | T | query/ORM | `expected.add` | ver matriz |
| `scripts/facial_runtime_layer_probe.py:33` / `verify_export` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/facial_runtime_layer_probe.py:23` / `verify_export` | T | query/ORM | `allowed.add` | ver matriz |
| `scripts/facial_runtime_layer_probe.py:50` / `verify_export` | T | query/ORM | `found.add` | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py:33` / `create_with_synthetic_tenant` | T | query/ORM | `db.get` | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py:34` / `create_with_synthetic_tenant` | T | query/ORM | `db.add` | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py:51` / `main` | T | query/ORM | `db.scalars` | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py:52` / `main` | T | query/ORM | `db.scalars` | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py:34` / `create_with_synthetic_tenant` | T | produtor | `Tenant` | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py:51` / `main` | T | query/ORM | `select` | ver matriz |
| `scripts/facial_runtime_native_rehearsal.py:52` / `main` | T | query/ORM | `select` | ver matriz |
| `scripts/facial_runtime_restoration.py:71` / `validate_inventory` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:92` / `validate_images` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:97` / `validate_images` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:107` / `validate_images` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:109` / `validate_images` | T | query/ORM | `baseline.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:116` / `validate_images` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:120` / `validate_images` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:142` / `calibration_admission_proven` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:112` / `validate_images` | T | query/ORM | `baseline.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:112` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:118` / `validate_images` | T | query/ORM | `baseline.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:118` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:143` / `calibration_admission_proven` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:145` / `calibration_admission_proven` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:147` / `calibration_admission_proven` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:148` / `calibration_admission_proven` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:149` / `calibration_admission_proven` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:150` / `calibration_admission_proven` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:282` / `execute` | T | efeito potencial | `host.replace` | ver matriz |
| `scripts/facial_runtime_restoration.py:62` / `validate_inventory` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:62` / `validate_inventory` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:63` / `validate_inventory` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:63` / `validate_inventory` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:64` / `validate_inventory` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:75` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:76` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:77` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:81` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:83` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:85` / `validate_inventory` | T | query/ORM | `services[service].get` | ver matriz |
| `scripts/facial_runtime_restoration.py:86` / `validate_inventory` | T | query/ORM | `services[service].get` | ver matriz |
| `scripts/facial_runtime_restoration.py:90` / `validate_images` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:90` / `validate_images` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:101` / `validate_images` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:102` / `validate_images` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:104` / `validate_images` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:106` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:106` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:108` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:108` / `validate_images` | T | query/ORM | `baseline.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:191` / `execute` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:192` / `execute` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:273` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:274` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:275` / `execute` | T | query/ORM | `affected.add` | ver matriz |
| `scripts/facial_runtime_restoration.py:74` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:96` / `validate_images` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:105` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:105` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:111` / `validate_images` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:203` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:226` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:297` / `execute` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:297` / `execute` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:79` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:79` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:205` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:205` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:206` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:209` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:210` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:211` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:213` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:218` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:235` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:257` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:264` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:212` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:214` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:217` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:228` / `execute` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:228` / `execute` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:234` / `execute` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:237` / `execute` | T | query/ORM | `current_proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:238` / `execute` | T | query/ORM | `current_proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:240` / `execute` | T | query/ORM | `current_proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:241` / `execute` | T | query/ORM | `current_proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:243` / `execute` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:243` / `execute` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:245` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:245` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:246` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:246` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:247` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:260` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:260` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration.py:261` / `execute` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration_cli.py:71` / `_inventory_summary` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_cli.py:76` / `_inventory_summary` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_cli.py:77` / `_inventory_summary` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_cli.py:80` / `_inventory_summary` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_cli.py:81` / `_inventory_summary` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_cli.py:82` / `_inventory_summary` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:174` / `environment` | T | query/ORM | `item['Config'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:182` / `configuration` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:183` / `configuration` | T | query/ORM | `m.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:188` / `configuration` | T | query/ORM | `host.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:203` / `_escape` | T | efeito potencial | `value.replace` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:363` / `_write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:368` / `_write` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:369` / `_write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:417` / `_compose_files` | T | query/ORM | `item['Config'].get('Labels', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:518` / `prepare` | T | efeito potencial | `AESGCM(key).encrypt` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:615` / `_restart_option` | T | query/ORM | `policy.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:617` / `_restart_option` | T | query/ORM | `policy.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:813` / `_target_environment` | T | query/ORM | `result.update` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:873` / `replace` | T | query/ORM | `baseline['Config'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:874` / `replace` | T | query/ORM | `baseline['Config'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:918` / `align_notifications` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:921` / `align_notifications` | T | query/ORM | `record.get('active_ids', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:942` / `align_notifications` | T | query/ORM | `alignment.update` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:960` / `align_notifications` | T | query/ORM | `alignment.update` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1047` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1066` / `functional_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1076` / `functional_proof` | T | query/ORM | `proof.update` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1091` / `complete` | T | efeito potencial | `journal.unlink` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1092` / `complete` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `item.get('NetworkSettings', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:345` / `_read_file` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:390` / `lock` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:448` / `inventory` | T | query/ORM | `item['Config'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:449` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:471` / `inventory` | T | query/ORM | `{'aarch64': 'arm64', 'arm64': 'arm64'}.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:510` / `prepare` | T | query/ORM | `self._raw[service]['Config'].get('Labels', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:614` / `_restart_option` | T | query/ORM | `item.get('HostConfig', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:636` / `_restore_stopped` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:678` / `quiesce` | T | query/ORM | `record.get('active_ids', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:701` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:704` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:811` / `_target_environment` | T | query/ORM | `result.update` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:812` / `_target_environment` | T | query/ORM | `saved.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:826` / `replace` | T | query/ORM | `record.get('active_ids', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:922` / `align_notifications` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:949` / `align_notifications` | T | efeito potencial | `self.replace` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1007` / `activation_proof` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1015` / `activation_proof` | T | query/ORM | `saved.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:264` / `_assert_preserved_layer` | T | query/ORM | `allowed.add` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:417` / `_compose_files` | T | query/ORM | `item['Config'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:467` / `inventory` | T | query/ORM | `item['State'].get('Health', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:467` / `inventory` | T | query/ORM | `environment(item).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:467` / `inventory` | T | query/ORM | `environment(item).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:467` / `inventory` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:550` / `_private` | T | efeito potencial | `AESGCM(key).decrypt` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:574` / `_current` | T | query/ORM | `selected.get('Config', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:629` / `_assert_known_process` | T | query/ORM | `item.get('Config', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:828` / `replace` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:869` / `replace` | T | query/ORM | `model.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:921` / `align_notifications` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1082` / `complete` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1082` / `complete` | T | query/ORM | `result.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:259` / `_assert_preserved_layer` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:450` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:474` / `prove_images` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:481` / `prove_images` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:483` / `prove_images` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:492` / `_probe_image` | T | query/ORM | `info[0].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:492` / `_probe_image` | T | query/ORM | `info[0].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:492` / `_probe_image` | T | query/ORM | `info[0].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:510` / `prepare` | T | query/ORM | `self._raw[service]['Config'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:541` / `candidate_manifest` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:590` / `_refresh_nginx_api_upstream` | T | query/ORM | `item['State'].get('Health', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:598` / `_refresh_nginx_api_upstream` | T | query/ORM | `current['State'].get('Health', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:614` / `_restart_option` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:630` / `_assert_known_process` | T | query/ORM | `item.get('State', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:652` / `_restore_stopped` | T | query/ORM | `item['State'].get('Health', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:678` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:680` / `quiesce` | T | query/ORM | `record.get('previous_ids', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:702` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:702` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:740` / `quiesce` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:826` / `replace` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:931` / `align_notifications` | T | query/ORM | `record.get('notification_alignment', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:955` / `align_notifications` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:955` / `align_notifications` | T | query/ORM | `observed.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:986` / `verify` | T | query/ORM | `actual['State'].get('Health', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1002` / `activation_proof` | T | query/ORM | `evidence.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1002` / `activation_proof` | T | query/ORM | `evidence.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1002` / `activation_proof` | T | query/ORM | `evidence.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1003` / `activation_proof` | T | query/ORM | `evidence.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1017` / `activation_proof` | T | query/ORM | `saved.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1039` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1039` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1040` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1041` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1042` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1043` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1044` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1045` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1049` / `recovery_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1053` / `recovery_proof` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1054` / `recovery_proof` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1055` / `recovery_proof` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1056` / `recovery_proof` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1061` / `functional_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1061` / `functional_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1068` / `functional_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1075` / `functional_proof` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1075` / `functional_proof` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1081` / `complete` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1081` / `complete` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1081` / `complete` | T | query/ORM | `result.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:467` / `inventory` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:479` / `prove_images` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:515` / `prepare` | T | query/ORM | `receipt['manifest'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:516` / `prepare` | T | query/ORM | `receipt['manifest'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:574` / `_current` | T | query/ORM | `selected.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:575` / `_current` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:576` / `_current` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:629` / `_assert_known_process` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:660` / `_restore_stopped` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:671` / `quiesce` | T | query/ORM | `record.get('active_ids', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:680` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:688` / `quiesce` | T | query/ORM | `environment(item).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:692` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:839` / `replace` | T | query/ORM | `current['State'].get('Health', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:858` / `replace` | T | query/ORM | `current['State'].get('Health', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:894` / `replace` | T | query/ORM | `current.get('HostConfig', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:895` / `replace` | T | query/ORM | `current.get('HostConfig', {}).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1006` / `activation_proof` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1012` / `activation_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1012` / `activation_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1012` / `activation_proof` | T | query/ORM | `value.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1019` / `activation_proof` | T | query/ORM | `decision.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1020` / `activation_proof` | T | query/ORM | `decision.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1022` / `activation_proof` | T | query/ORM | `environment(api).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1023` / `activation_proof` | T | query/ORM | `environment(api).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1026` / `activation_proof` | T | query/ORM | `environment(api).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1027` / `activation_proof` | T | query/ORM | `environment(api).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:192` / `configuration` | T | query/ORM | `config.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:590` / `_refresh_nginx_api_upstream` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:598` / `_refresh_nginx_api_upstream` | T | query/ORM | `current['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:630` / `_assert_known_process` | T | query/ORM | `item.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:652` / `_restore_stopped` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:680` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:693` / `quiesce` | T | query/ORM | `environment(item).get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:764` / `quiesce` | T | query/ORM | `stopped['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:919` / `align_notifications` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:931` / `align_notifications` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:968` / `verify` | T | query/ORM | `actual['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:968` / `verify` | T | query/ORM | `baseline['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:986` / `verify` | T | query/ORM | `actual['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:671` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:681` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:681` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:753` / `quiesce` | T | query/ORM | `state.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:839` / `replace` | T | query/ORM | `current['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:858` / `replace` | T | query/ORM | `current['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:894` / `replace` | T | query/ORM | `current.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:895` / `replace` | T | query/ORM | `current.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:1032` / `activation_proof` | T | query/ORM | `saved.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:467` / `inventory` | T | query/ORM | `item['HostConfig'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:727` / `quiesce` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:731` / `quiesce` | T | query/ORM | `record.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:728` / `quiesce` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:728` / `quiesce` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:729` / `quiesce` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:729` / `quiesce` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:730` / `quiesce` | T | query/ORM | `entry.get` | ver matriz |
| `scripts/facial_runtime_restoration_host.py:730` / `quiesce` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/local_photographer_demo.py:27` / `reject_postgres_routing_overrides` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_photographer_demo.py:29` / `reject_postgres_routing_overrides` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_photographer_demo.py:37` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_photographer_demo.py:79` / `configure_synthetic_environment` | T | query/ORM | `os.environ.update` | ver matriz |
| `scripts/local_photographer_demo.py:175` / `main` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/local_photographer_demo.py:227` / `main` | T | query/ORM | `application.app.get` | ver matriz |
| `scripts/local_photographer_demo.py:242` / `local_request` | T | query/ORM | `db.scalar` | ver matriz |
| `scripts/local_photographer_demo.py:35` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_photographer_demo.py:35` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_photographer_demo.py:114` / `refresh_disabled_synthetic_owner` | T | efeito potencial | `TotpSecretCipher.from_environment().encrypt` | ver matriz |
| `scripts/local_photographer_demo.py:115` / `refresh_disabled_synthetic_owner` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/local_photographer_demo.py:147` / `create_synthetic_owner` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/local_photographer_demo.py:151` / `create_synthetic_owner` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/local_photographer_demo.py:257` / `simulate_credit_purchase` | T | query/ORM | `db.scalar` | ver matriz |
| `scripts/local_photographer_demo.py:279` / `configure_upload_prerequisites` | T | query/ORM | `db.scalar` | ver matriz |
| `scripts/local_photographer_demo.py:115` / `refresh_disabled_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_photographer_demo.py:137` / `create_synthetic_owner` | T | efeito potencial | `TotpSecretCipher.from_environment().encrypt` | ver matriz |
| `scripts/local_photographer_demo.py:138` / `create_synthetic_owner` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/local_photographer_demo.py:143` / `create_synthetic_owner` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/local_photographer_demo.py:147` / `create_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_photographer_demo.py:151` / `create_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_photographer_demo.py:277` / `configure_upload_prerequisites` | T | query/ORM | `wallet.get` | ver matriz |
| `scripts/local_photographer_demo.py:106` / `refresh_disabled_synthetic_owner` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/local_photographer_demo.py:129` / `create_synthetic_owner` | T | query/ORM | `connection.execute(text('SELECT id FROM tenant ORDER BY id')).scalars` | ver matriz |
| `scripts/local_photographer_demo.py:130` / `create_synthetic_owner` | T | query/ORM | `connection.scalar` | ver matriz |
| `scripts/local_photographer_demo.py:138` / `create_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_photographer_demo.py:143` / `create_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_photographer_demo.py:242` / `local_request` | T | query/ORM | `select` | ver matriz |
| `scripts/local_photographer_demo.py:106` / `refresh_disabled_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_photographer_demo.py:130` / `create_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_photographer_demo.py:257` / `simulate_credit_purchase` | T | query/ORM | `select` | ver matriz |
| `scripts/local_photographer_demo.py:279` / `configure_upload_prerequisites` | T | query/ORM | `select` | ver matriz |
| `scripts/local_photographer_demo.py:129` / `create_synthetic_owner` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/local_photographer_demo.py:129` / `create_synthetic_owner` | T | query/ORM | `text` | ver matriz |
| `scripts/local_tenant_closure_demo.py:26` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_tenant_closure_demo.py:154` / `main` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/local_tenant_closure_demo.py:22` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_tenant_closure_demo.py:23` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_tenant_closure_demo.py:30` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_tenant_closure_demo.py:30` / `validate_target` | T | query/ORM | `environment.get` | ver matriz |
| `scripts/local_tenant_closure_demo.py:61` / `seed_accounts` | T | query/ORM | `db.scalar` | ver matriz |
| `scripts/local_tenant_closure_demo.py:62` / `seed_accounts` | T | query/ORM | `db.get` | ver matriz |
| `scripts/local_tenant_closure_demo.py:70` / `seed_accounts` | T | query/ORM | `db.scalar` | ver matriz |
| `scripts/local_tenant_closure_demo.py:73` / `seed_accounts` | T | produtor | `Tenant` | ver matriz |
| `scripts/local_tenant_closure_demo.py:74` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:76` / `seed_accounts` | T | produtor | `AdminUser` | ver matriz |
| `scripts/local_tenant_closure_demo.py:80` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:82` / `seed_accounts` | T | query/ORM | `db.add_all` | ver matriz |
| `scripts/local_tenant_closure_demo.py:87` / `seed_accounts` | T | query/ORM | `db.add_all` | ver matriz |
| `scripts/local_tenant_closure_demo.py:101` / `seed_accounts` | T | produtor | `ParentGallery` | ver matriz |
| `scripts/local_tenant_closure_demo.py:102` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:104` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:109` / `seed_accounts` | T | produtor | `Tenant` | ver matriz |
| `scripts/local_tenant_closure_demo.py:110` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:112` / `seed_accounts` | T | produtor | `AdminUser` | ver matriz |
| `scripts/local_tenant_closure_demo.py:116` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:118` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:119` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:125` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:131` / `seed_accounts` | T | query/ORM | `db.add` | ver matriz |
| `scripts/local_tenant_closure_demo.py:61` / `seed_accounts` | T | query/ORM | `select` | ver matriz |
| `scripts/local_tenant_closure_demo.py:71` / `seed_accounts` | T | query/ORM | `db.get` | ver matriz |
| `scripts/local_tenant_closure_demo.py:104` / `seed_accounts` | T | produtor | `PhotoFolder` | ver matriz |
| `scripts/local_tenant_closure_demo.py:118` / `seed_accounts` | T | produtor | `TenantAdmin` | ver matriz |
| `scripts/local_tenant_closure_demo.py:119` / `seed_accounts` | T | produtor | `TenantCreditWallet` | ver matriz |
| `scripts/local_tenant_closure_demo.py:125` / `seed_accounts` | T | produtor | `PhotographerBusinessProfile` | ver matriz |
| `scripts/local_tenant_closure_demo.py:131` / `seed_accounts` | T | produtor | `TenantClosureRequest` | ver matriz |
| `scripts/local_tenant_closure_demo.py:83` / `seed_accounts` | T | produtor | `TenantAdmin` | ver matriz |
| `scripts/local_tenant_closure_demo.py:84` / `seed_accounts` | T | produtor | `TenantCreditWallet` | ver matriz |
| `scripts/local_tenant_closure_demo.py:88` / `seed_accounts` | T | produtor | `PhotographerSignup` | ver matriz |
| `scripts/local_tenant_closure_demo.py:93` / `seed_accounts` | T | produtor | `PhotographerTermsAcceptance` | ver matriz |
| `scripts/local_tenant_closure_demo.py:70` / `seed_accounts` | T | query/ORM | `select` | ver matriz |
| `scripts/local_tenant_closure_demo.py:127` / `seed_accounts` | T | efeito potencial | `encrypt_private_field` | ver matriz |
| `scripts/local_tenant_closure_demo.py:128` / `seed_accounts` | T | efeito potencial | `encrypt_private_document` | ver matriz |
| `scripts/nginx_compose_provenance.py:238` / `private_write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/nginx_compose_provenance.py:243` / `private_write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/nginx_compose_provenance.py:106` / `validate_runtime` | T | query/ORM | `c['Config'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:118` / `matches_image_config` | T | query/ORM | `image_config.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:127` / `validate_runtime` | T | query/ORM | `h.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:128` / `validate_runtime` | T | query/ORM | `h.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:129` / `validate_runtime` | T | query/ORM | `h.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:137` / `validate_runtime` | T | query/ORM | `h.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:154` / `healthcheck_model` | T | query/ORM | `value.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:183` / `candidate_model` | T | query/ORM | `config.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:112` / `validate_runtime` | T | query/ORM | `c['Config'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:125` / `validate_runtime` | T | query/ORM | `c['Config'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:134` / `validate_runtime` | T | query/ORM | `h.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:170` / `candidate_model` | T | efeito potencial | `v.replace` | ver matriz |
| `scripts/nginx_compose_provenance.py:229` / `private_read` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/nginx_compose_provenance.py:255` / `exclusive_lock` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/nginx_compose_provenance.py:279` / `configuration_projection` | T | query/ORM | `config.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:107` / `validate_runtime` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:108` / `validate_runtime` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:109` / `validate_runtime` | T | query/ORM | `c['State'].get('Health', {}).get` | ver matriz |
| `scripts/nginx_compose_provenance.py:170` / `candidate_model` | T | query/ORM | `config.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:205` / `validate_payload` | T | query/ORM | `payload.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:205` / `validate_payload` | T | query/ORM | `payload.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:206` / `validate_payload` | T | query/ORM | `payload.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:442` / `graceful_stop` | T | query/ORM | `container['Config'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:452` / `verify_running` | T | query/ORM | `c['State'].get('Health', {}).get` | ver matriz |
| `scripts/nginx_compose_provenance.py:459` / `verify_running` | T | query/ORM | `observed['host'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:459` / `verify_running` | T | query/ORM | `expected['host'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:176` / `candidate_model` | T | query/ORM | `data.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:310` / `snapshot` | T | query/ORM | `c['Config']['Labels'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:369` / `validate_model` | T | query/ORM | `model.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:372` / `validate_model` | T | query/ORM | `service.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:373` / `validate_model` | T | query/ORM | `service.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:373` / `validate_model` | T | query/ORM | `service.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:431` / `peers_unchanged` | T | query/ORM | `x['Config']['Labels'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:436` / `target` | T | query/ORM | `c['Config']['Labels'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:483` / `verify_running` | T | query/ORM | `observed_mounts.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:483` / `verify_running` | T | query/ORM | `expected_mounts.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:109` / `validate_runtime` | T | query/ORM | `c['State'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:132` / `validate_runtime` | T | query/ORM | `defaults.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:288` / `configuration_projection` | T | query/ORM | `c['Config'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:290` / `configuration_projection` | T | query/ORM | `n.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:304` / `containers` | T | query/ORM | `x['Config']['Labels'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:452` / `verify_running` | T | query/ORM | `c['State'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:502` / `recover` | T | query/ORM | `current['Config']['Labels'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:143` / `validate_runtime` | T | query/ORM | `n.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:143` / `validate_runtime` | T | query/ORM | `n.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:179` / `candidate_model` | T | query/ORM | `config.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:331` / `snapshot` | T | query/ORM | `x['State'].get('Health', {}).get` | ver matriz |
| `scripts/nginx_compose_provenance.py:511` / `recover` | T | query/ORM | `data.get` | ver matriz |
| `scripts/nginx_compose_provenance.py:566` / `release` | T | query/ORM, efeito potencial | `published['Config']['Labels'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:567` / `release` | T | query/ORM, efeito potencial | `published['Config']['Labels'].get` | ver matriz |
| `scripts/nginx_compose_provenance.py:331` / `snapshot` | T | query/ORM | `x['State'].get` | ver matriz |
| `scripts/orders_pilot_release.py:164` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:173` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:194` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:981` / `save` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/orders_pilot_release.py:1054` / `prepare` | T | efeito potencial | `(context / 'Dockerfile.backend').write_text` | ver matriz |
| `scripts/orders_pilot_release.py:1066` / `prepare` | T | efeito potencial | `(context / 'Dockerfile.web').write_text` | ver matriz |
| `scripts/orders_pilot_release.py:1069` / `prepare` | T | efeito potencial | `(context / '.dockerignore').write_text` | ver matriz |
| `scripts/orders_pilot_release.py:1237` / `apply` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:371` / `is_remote_ancestor` | T | query/ORM | `comparison.get` | ver matriz |
| `scripts/orders_pilot_release.py:372` / `is_remote_ancestor` | T | query/ORM | `comparison.get` | ver matriz |
| `scripts/orders_pilot_release.py:436` / `inventory` | T | efeito potencial | `self.published_orders` | ver matriz |
| `scripts/orders_pilot_release.py:544` / `live_gate_inventory` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/orders_pilot_release.py:962` / `restore_before_ddl` | T | query/ORM | `load(work / 'stage.json').get` | ver matriz |
| `scripts/orders_pilot_release.py:983` / `save` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/orders_pilot_release.py:999` / `extract` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/orders_pilot_release.py:1086` / `prepare` | T | efeito potencial | `key_copy.open` | ver matriz |
| `scripts/orders_pilot_release.py:1093` / `prepare` | T | efeito potencial | `previous_identity.open` | ver matriz |
| `scripts/orders_pilot_release.py:1197` / `release_lock` | T | efeito potencial | `path.open` | ver matriz |
| `scripts/orders_pilot_release.py:1208` / `validate_upgrade_receipt` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1267` / `apply` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/orders_pilot_release.py:1365` / `resume` | T | query/ORM | `stage.update` | ver matriz |
| `scripts/orders_pilot_release.py:1367` / `resume` | T | efeito potencial | `publish_identity` | ver matriz |
| `scripts/orders_pilot_release.py:1368` / `resume` | T | efeito potencial | `marker.unlink` | ver matriz |
| `scripts/orders_pilot_release.py:1387` / `recover` | T | efeito potencial | `marker.unlink` | ver matriz |
| `scripts/orders_pilot_release.py:168` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:170` / `validate_inventory` | T | query/ORM | `data['key'].get` | ver matriz |
| `scripts/orders_pilot_release.py:171` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:172` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:184` / `validate_inventory` | T | query/ORM | `services['api'].get` | ver matriz |
| `scripts/orders_pilot_release.py:185` / `validate_inventory` | T | query/ORM | `services['worker'].get` | ver matriz |
| `scripts/orders_pilot_release.py:193` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:251` / `current_test_pair` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:262` / `current_test_pair` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:445` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/orders_pilot_release.py:520` / `live_gate_inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/orders_pilot_release.py:523` / `live_gate_inventory` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/orders_pilot_release.py:524` / `live_gate_inventory` | T | query/ORM | `d['State'].get('Health', {}).get` | ver matriz |
| `scripts/orders_pilot_release.py:541` / `live_gate_inventory` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/orders_pilot_release.py:977` / `save` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/orders_pilot_release.py:1009` / `extract` | T | efeito potencial | `dest.write_bytes` | ver matriz |
| `scripts/orders_pilot_release.py:1234` / `apply` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1235` / `apply` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1236` / `apply` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1242` / `apply` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1302` / `apply` | T | efeito potencial | `publish_identity` | ver matriz |
| `scripts/orders_pilot_release.py:1303` / `apply` | T | efeito potencial | `marker.unlink` | ver matriz |
| `scripts/orders_pilot_release.py:155` / `package_parity` | T | query/ORM | `before['packages'].get` | ver matriz |
| `scripts/orders_pilot_release.py:160` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:160` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:161` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:161` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:162` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:162` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:163` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:163` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:165` / `validate_inventory` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:166` / `validate_inventory` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:167` / `validate_inventory` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:169` / `validate_inventory` | T | query/ORM | `data.get('key', {}).get` | ver matriz |
| `scripts/orders_pilot_release.py:169` / `validate_inventory` | T | query/ORM | `data['key'].get` | ver matriz |
| `scripts/orders_pilot_release.py:190` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:195` / `validate_inventory` | T | query/ORM | `pillow.get` | ver matriz |
| `scripts/orders_pilot_release.py:195` / `validate_inventory` | T | query/ORM | `pillow.get` | ver matriz |
| `scripts/orders_pilot_release.py:196` / `validate_inventory` | T | query/ORM | `pillow.get` | ver matriz |
| `scripts/orders_pilot_release.py:375` / `is_remote_ancestor` | T | query/ORM | `base.get` | ver matriz |
| `scripts/orders_pilot_release.py:377` / `is_remote_ancestor` | T | query/ORM | `comparison.get` | ver matriz |
| `scripts/orders_pilot_release.py:444` / `inventory` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/orders_pilot_release.py:457` / `inventory` | T | query/ORM | `d['State'].get('Health', {}).get` | ver matriz |
| `scripts/orders_pilot_release.py:458` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/orders_pilot_release.py:461` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/orders_pilot_release.py:462` / `inventory` | T | query/ORM | `d['NetworkSettings'].get` | ver matriz |
| `scripts/orders_pilot_release.py:462` / `inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:464` / `inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:519` / `live_gate_inventory` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/orders_pilot_release.py:526` / `live_gate_inventory` | T | query/ORM | `d['NetworkSettings'].get` | ver matriz |
| `scripts/orders_pilot_release.py:532` / `live_gate_inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:533` / `live_gate_inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/orders_pilot_release.py:534` / `live_gate_inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/orders_pilot_release.py:542` / `live_gate_inventory` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/orders_pilot_release.py:547` / `live_gate_inventory` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/orders_pilot_release.py:706` / `callback_rehearsal` | T | query/ORM | `result.get` | ver matriz |
| `scripts/orders_pilot_release.py:716` / `guard_rehearsal` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/orders_pilot_release.py:778` / `file_command` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/orders_pilot_release.py:883` / `wait_healthy` | T | query/ORM | `d['State'].get('Health', {}).get` | ver matriz |
| `scripts/orders_pilot_release.py:1138` / `owner_check` | T | efeito potencial | `h.published_orders` | ver matriz |
| `scripts/orders_pilot_release.py:1206` / `validate_upgrade_receipt` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1206` / `validate_upgrade_receipt` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1239` / `apply` | T | query/ORM | `callbacks.get` | ver matriz |
| `scripts/orders_pilot_release.py:1240` / `apply` | T | query/ORM | `callbacks.get` | ver matriz |
| `scripts/orders_pilot_release.py:1248` / `apply` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:1408` / `main` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:176` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/orders_pilot_release.py:176` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/orders_pilot_release.py:177` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/orders_pilot_release.py:177` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/orders_pilot_release.py:182` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/orders_pilot_release.py:249` / `current_test_pair` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:249` / `current_test_pair` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:260` / `current_test_pair` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:260` / `current_test_pair` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:260` / `current_test_pair` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:260` / `current_test_pair` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:276` / `published_orders` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:276` / `published_orders` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:277` / `published_orders` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:277` / `published_orders` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:278` / `published_orders` | T | query/ORM | `identity.get` | ver matriz |
| `scripts/orders_pilot_release.py:282` / `published_orders` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:282` / `published_orders` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/orders_pilot_release.py:375` / `is_remote_ancestor` | T | query/ORM | `merge_base.get` | ver matriz |
| `scripts/orders_pilot_release.py:423` / `pillow` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/orders_pilot_release.py:423` / `pillow` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/orders_pilot_release.py:424` / `pillow` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/orders_pilot_release.py:424` / `pillow` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/orders_pilot_release.py:425` / `pillow` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/orders_pilot_release.py:425` / `pillow` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/orders_pilot_release.py:524` / `live_gate_inventory` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/orders_pilot_release.py:537` / `live_gate_inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:784` / `file_command` | T | efeito potencial | `path.open` | ver matriz |
| `scripts/orders_pilot_release.py:1226` / `publish_identity` | T | query/ORM | `current.get` | ver matriz |
| `scripts/orders_pilot_release.py:1226` / `publish_identity` | T | query/ORM | `current.get` | ver matriz |
| `scripts/orders_pilot_release.py:1227` / `publish_identity` | T | query/ORM | `current.get` | ver matriz |
| `scripts/orders_pilot_release.py:1308` / `apply` | T | efeito potencial | `marker.unlink` | ver matriz |
| `scripts/orders_pilot_release.py:1333` / `resume` | T | query/ORM | `stage.get` | ver matriz |
| `scripts/orders_pilot_release.py:1333` / `resume` | T | query/ORM | `stage.get` | ver matriz |
| `scripts/orders_pilot_release.py:1347` / `resume` | T | query/ORM | `d['Config'].get('Labels', {}).get` | ver matriz |
| `scripts/orders_pilot_release.py:1380` / `recover` | T | query/ORM | `stage.get` | ver matriz |
| `scripts/orders_pilot_release.py:1380` / `recover` | T | query/ORM | `stage.get` | ver matriz |
| `scripts/orders_pilot_release.py:169` / `validate_inventory` | T | query/ORM | `data.get` | ver matriz |
| `scripts/orders_pilot_release.py:447` / `inventory` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/orders_pilot_release.py:449` / `inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:452` / `inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:457` / `inventory` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/orders_pilot_release.py:473` / `inventory` | T | query/ORM | `key_config.get` | ver matriz |
| `scripts/orders_pilot_release.py:522` / `live_gate_inventory` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/orders_pilot_release.py:628` / `verify_ci` | T | query/ORM | `r.get` | ver matriz |
| `scripts/orders_pilot_release.py:629` / `verify_ci` | T | query/ORM | `r.get` | ver matriz |
| `scripts/orders_pilot_release.py:629` / `verify_ci` | T | query/ORM | `r.get` | ver matriz |
| `scripts/orders_pilot_release.py:629` / `verify_ci` | T | query/ORM | `r.get` | ver matriz |
| `scripts/orders_pilot_release.py:631` / `verify_ci` | T | query/ORM | `r.get` | ver matriz |
| `scripts/orders_pilot_release.py:704` / `callback_rehearsal` | T | query/ORM | `result.get` | ver matriz |
| `scripts/orders_pilot_release.py:744` / `guard_rehearsal` | T | query/ORM | `d['Config']['Labels'].get` | ver matriz |
| `scripts/orders_pilot_release.py:764` / `web_shutdown_rehearsal` | T | query/ORM | `d['Config']['Labels'].get` | ver matriz |
| `scripts/orders_pilot_release.py:831` / `rehearse` | T | query/ORM | `d['Config']['Labels'].get` | ver matriz |
| `scripts/orders_pilot_release.py:856` / `maintenance` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/orders_pilot_release.py:883` / `wait_healthy` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/orders_pilot_release.py:1238` / `apply` | T | query/ORM | `callbacks.get` | ver matriz |
| `scripts/orders_pilot_release.py:179` / `validate_inventory` | T | query/ORM | `item.get` | ver matriz |
| `scripts/orders_pilot_release.py:188` / `validate_inventory` | T | query/ORM | `services[name].get` | ver matriz |
| `scripts/orders_pilot_release.py:199` / `validate_inventory` | T | query/ORM | `services[service].get` | ver matriz |
| `scripts/orders_pilot_release.py:473` / `inventory` | T | query/ORM | `api_env.get` | ver matriz |
| `scripts/orders_pilot_release.py:473` / `inventory` | T | query/ORM | `key_config.get` | ver matriz |
| `scripts/orders_pilot_release.py:690` / `shutdown_rehearsal` | T | query/ORM | `d['Config']['Labels'].get` | ver matriz |
| `scripts/orders_pilot_release.py:895` / `wait_new` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:895` / `wait_new` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:896` / `wait_new` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:1347` / `resume` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/orders_pilot_release.py:899` / `wait_new` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:565` / `live_gate_inventory` | T | query/ORM | `self.inspect(i, diagnostic_stage='locate_api_container')['Config'].get('Labels', {}).get` | ver matriz |
| `scripts/orders_pilot_release.py:898` / `wait_new` | T | query/ORM | `env.get` | ver matriz |
| `scripts/orders_pilot_release.py:565` / `live_gate_inventory` | T | query/ORM | `self.inspect(i, diagnostic_stage='locate_api_container')['Config'].get` | ver matriz |
| `scripts/prepare_emergency_api_image.py:31` / `maintenance_configuration` | T | efeito potencial | `server.replace` | ver matriz |
| `scripts/prepare_emergency_api_image.py:137` / `prepare` | T | efeito potencial | `receipt.write_text` | ver matriz |
| `scripts/prepare_emergency_api_image.py:44` / `maintenance` | T | efeito potencial | `marker.unlink` | ver matriz |
| `scripts/prepare_emergency_api_image.py:65` / `maintenance` | T | efeito potencial | `marker.write_text` | ver matriz |
| `scripts/prepare_emergency_api_image.py:98` / `extract_source` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/prepare_emergency_api_image.py:127` / `prepare` | T | efeito potencial | `(root / 'Dockerfile').write_text` | ver matriz |
| `scripts/prepare_emergency_api_image.py:108` / `extract_source` | T | efeito potencial | `target.write_bytes` | ver matriz |
| `scripts/preserve_branding.py:234` / `preserve` | T | query/ORM | `settings.get` | ver matriz |
| `scripts/preserve_branding.py:80` / `settings_keys` | T | query/ORM | `owners.add` | ver matriz |
| `scripts/preserve_branding.py:176` / `extract_asset` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/preserve_branding.py:203` / `receive_backup` | T | efeito potencial | `(backup / 'manifest.json').write_text` | ver matriz |
| `scripts/preserve_branding.py:252` / `preserve` | T | query/ORM | `volume_info.get` | ver matriz |
| `scripts/preserve_branding.py:255` / `preserve` | T | query/ORM | `volume_info.get` | ver matriz |
| `scripts/preserve_branding.py:297` / `preserve` | T | efeito potencial | `(backup / 'manifest.json').write_text` | ver matriz |
| `scripts/preserve_branding.py:142` / `transfer` | T | efeito potencial | `Path(temporary).unlink` | ver matriz |
| `scripts/preserve_branding.py:167` / `container` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:167` / `container` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:202` / `receive_backup` | T | efeito potencial | `(backup / key).write_bytes` | ver matriz |
| `scripts/preserve_branding.py:253` / `preserve` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:253` / `preserve` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:255` / `preserve` | T | query/ORM | `volume_info.get` | ver matriz |
| `scripts/preserve_branding.py:294` / `preserve` | T | efeito potencial | `(backup / key).open` | ver matriz |
| `scripts/preserve_branding.py:306` / `preserve` | T | efeito potencial | `override.open` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:59` / `web_classification` | T | query/ORM | `container.get('HostConfig', {}).get('RestartPolicy', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:60` / `web_classification` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:61` / `web_classification` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:62` / `web_classification` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:63` / `web_classification` | T | query/ORM | `container.get('Config', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:64` / `web_classification` | T | query/ORM | `container.get('State', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:65` / `web_classification` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:158` / `historical_identity` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:164` / `historical_identity` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:58` / `web_classification` | T | query/ORM | `container.get('Config', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:96` / `sanitized_container_summary` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:98` / `sanitized_container_summary` | T | query/ORM | `container.get('State', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:103` / `sanitized_container_summary` | T | query/ORM | `seen.add` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:123` / `validate_service_identity` | T | query/ORM | `services[name].get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:153` / `historical_identity` | T | query/ORM | `container.get('Config', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:155` / `historical_identity` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:155` / `historical_identity` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:202` / `historical_mount_diagnostics` | T | query/ORM | `mount.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:234` / `partition_containers` | T | query/ORM | `item.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:237` / `partition_containers` | T | query/ORM | `ids.add` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:242` / `partition_containers` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:249` / `partition_containers` | T | query/ORM | `services.add` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:322` / `_validate_inventory` | T | query/ORM | `historical_ids.add` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:693` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:59` / `web_classification` | T | query/ORM | `container.get('HostConfig', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:63` / `web_classification` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:64` / `web_classification` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:76` / `web_classification` | T | query/ORM | `{'True': 'sim', 'False': 'nao', 'true': 'sim', 'false': 'nao'}.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:94` / `sanitized_container_summary` | T | query/ORM | `container.get('Config', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:154` / `historical_identity` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:162` / `historical_identity` | T | query/ORM | `container.get('HostConfig', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:214` / `historical_field_hashes` | T | query/ORM | `item.get('State', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:232` / `partition_containers` | T | query/ORM | `item.get('Config', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:238` / `partition_containers` | T | query/ORM | `item.get('State', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:415` / `compose_files` | T | query/ORM | `paths.update` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:625` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:645` / `inventory` | T | query/ORM | `d['State'].get('Health', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:685` / `inventory` | T | query/ORM | `services.get('api', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:58` / `web_classification` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:75` / `web_classification` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:95` / `sanitized_container_summary` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:98` / `sanitized_container_summary` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:128` / `validate_service_identity` | T | query/ORM | `previous.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:128` / `validate_service_identity` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:153` / `historical_identity` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:159` / `historical_identity` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:159` / `historical_identity` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:160` / `historical_identity` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:160` / `historical_identity` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:171` / `historical_identity` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:233` / `partition_containers` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:241` / `partition_containers` | T | query/ORM | `item.get('State', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:260` / `select_candidate_ci` | T | query/ORM | `latest.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:260` / `select_candidate_ci` | T | query/ORM | `latest.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:261` / `select_candidate_ci` | T | query/ORM | `latest.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:387` / `lock` | T | efeito potencial | `lock_path.open` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:426` / `compose_files` | T | efeito potencial | `str(resolved.relative_to(ROOT)).replace` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:624` / `inventory` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:644` / `inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:649` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:650` / `inventory` | T | query/ORM | `env.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:59` / `web_classification` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:80` / `web_classification` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:94` / `sanitized_container_summary` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:162` / `historical_identity` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:214` / `historical_field_hashes` | T | query/ORM | `item.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:232` / `partition_containers` | T | query/ORM | `item.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:238` / `partition_containers` | T | query/ORM | `item.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:246` / `partition_containers` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:247` / `partition_containers` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:248` / `partition_containers` | T | query/ORM | `item.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:255` / `select_candidate_ci` | T | query/ORM | `run.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:256` / `select_candidate_ci` | T | query/ORM | `run.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:256` / `select_candidate_ci` | T | query/ORM | `run.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:257` / `select_candidate_ci` | T | query/ORM | `run.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:259` / `select_candidate_ci` | T | query/ORM | `run.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:259` / `select_candidate_ci` | T | query/ORM | `run.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:525` / `backup` | T | efeito potencial | `archive.open` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:576` / `candidate_commit_chain` | T | query/ORM | `result.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:577` / `candidate_commit_chain` | T | query/ORM | `result.get('base_commit', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:578` / `candidate_commit_chain` | T | query/ORM | `result.get('merge_base_commit', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:633` / `inventory` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:645` / `inventory` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:685` / `inventory` | T | query/ORM | `services.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:200` / `historical_mount_diagnostics` | T | query/ORM | `mount.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:241` / `partition_containers` | T | query/ORM | `item.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:514` / `backup` | T | query/ORM | `values.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:515` / `backup` | T | query/ORM | `values.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:515` / `backup` | T | query/ORM | `values.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:527` / `backup` | T | query/ORM | `hasher.update` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:529` / `backup` | T | query/ORM | `values.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:529` / `backup` | T | query/ORM | `values.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:532` / `backup` | T | efeito potencial | `archive.open` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:641` / `inventory` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:642` / `inventory` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:66` / `web_classification` | T | query/ORM | `m.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:577` / `candidate_commit_chain` | T | query/ORM | `result.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:578` / `candidate_commit_chain` | T | query/ORM | `result.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:176` / `historical_identity` | T | query/ORM | `mount.get` | ver matriz |
| `scripts/preview_adjustment_migration_inventory.py:646` / `inventory` | T | query/ORM | `d['NetworkSettings'].get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:142` / `record` | T | query/ORM | `self.journal.update` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:145` / `record` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:150` / `record` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:151` / `record` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:176` / `finish_journal` | T | efeito potencial | `JOURNAL.unlink` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:177` / `finish_journal` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:246` / `stage_candidate` | T | efeito potencial | `build_overlay.write_text` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:271` / `maintenance_configuration` | T | efeito potencial | `server.replace` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:507` / `backup_and_verify` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:525` / `apply_migration` | T | efeito potencial | `overlay.write_text` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:544` / `publish_api_web` | T | efeito potencial | `overlay.write_text` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:631` / `write_success_receipt` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:649` / `restore_before_migration` | T | query/ORM | `self.journal.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:170` / `finish_journal` | T | query/ORM | `self.journal.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:175` / `finish_journal` | T | efeito potencial | `shutil.rmtree` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:344` / `stop_writers` | T | query/ORM | `self.journal.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:501` / `backup_and_verify` | T | efeito potencial | `archive.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:606` / `wait_healthy` | T | query/ORM | `current['State'].get('Health', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:205` / `assert_historical_preserved` | T | query/ORM | `previous.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:206` / `assert_historical_preserved` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:283` / `maintenance` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:486` / `backup_and_verify` | T | efeito potencial | `archive.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:494` / `backup_and_verify` | T | efeito potencial | `archive.open` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:503` / `backup_and_verify` | T | query/ORM | `digest_builder.update` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:324` / `stop_writers` | T | query/ORM | `stop_order.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:519` / `assert_backup` | T | query/ORM | `backup.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:519` / `assert_backup` | T | query/ORM | `backup.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:520` / `assert_backup` | T | query/ORM | `backup.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:586` / `assert_runtime` | T | query/ORM | `current['State'].get('Health', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:594` / `assert_runtime` | T | query/ORM | `current['Config']['Labels'].get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:606` / `wait_healthy` | T | query/ORM | `current['State'].get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:572` / `assert_runtime` | T | query/ORM | `d['State'].get('Health', {}).get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:575` / `assert_runtime` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:577` / `assert_runtime` | T | query/ORM | `env.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:586` / `assert_runtime` | T | query/ORM | `current['State'].get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:208` / `assert_historical_preserved` | T | query/ORM | `old_fields.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:208` / `assert_historical_preserved` | T | query/ORM | `new_fields.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:356` / `stop_writers` | T | query/ORM | `d.get` | ver matriz |
| `scripts/preview_adjustment_migration_release.py:572` / `assert_runtime` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/preview_adjustment_migration_release_flow.py:91` / `execute` | T | efeito potencial | `host.publish_api_web` | ver matriz |
| `scripts/preview_adjustment_smoke.py:48` / `<módulo>` | T | query/ORM | `draw.text` | ver matriz |
| `scripts/preview_adjustment_smoke.py:49` / `<módulo>` | T | query/ORM | `draw.text` | ver matriz |
| `scripts/preview_worker_maintenance_flow.py:72` / `validate_preflight` | T | query/ORM | `report.get` | ver matriz |
| `scripts/preview_worker_maintenance_flow.py:90` / `validate_preflight` | T | query/ORM | `report.get` | ver matriz |
| `scripts/preview_worker_maintenance_flow.py:91` / `validate_preflight` | T | query/ORM | `report.get` | ver matriz |
| `scripts/preview_worker_maintenance_flow.py:83` / `validate_preflight` | T | query/ORM | `report.get` | ver matriz |
| `scripts/preview_worker_maintenance_flow.py:71` / `validate_preflight` | T | query/ORM | `report.get` | ver matriz |
| `scripts/preview_worker_maintenance_flow.py:87` / `validate_preflight` | T | query/ORM | `report.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:191` / `_service` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:199` / `_service` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:200` / `_service` | T | query/ORM | `state.get('Health', {}).get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:202` / `_service` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:203` / `_service` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:219` / `_service` | T | query/ORM | `restart.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:190` / `_service` | T | query/ORM | `container.get('Config', {}).get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:197` / `_service` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:197` / `_service` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:198` / `_service` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:201` / `_service` | T | query/ORM | `container.get('HostConfig', {}).get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:217` / `_service` | T | query/ORM | `restart.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:227` / `_service` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:193` / `_service` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:200` / `_service` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:241` / `_service` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:281` / `collect` | T | query/ORM | `candidate_info.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:313` / `collect` | T | query/ORM | `previous_info.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:314` / `collect` | T | query/ORM | `previous_info.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:190` / `_service` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:201` / `_service` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_worker_security_inventory.py:242` / `_service` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_journal.py:93` / `write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_worker_security_journal.py:99` / `write` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/preview_worker_security_journal.py:142` / `finish` | T | efeito potencial | `self.path.unlink` | ver matriz |
| `scripts/preview_worker_security_journal.py:66` / `write` | T | query/ORM | `value.get` | ver matriz |
| `scripts/preview_worker_security_journal.py:103` / `write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_worker_security_journal.py:132` / `read` | T | query/ORM | `value.get` | ver matriz |
| `scripts/preview_worker_security_journal.py:140` / `finish` | T | query/ORM | `value.get` | ver matriz |
| `scripts/preview_worker_security_journal.py:144` / `finish` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_worker_security_release_host.py:398` / `_maintenance_config` | T | efeito potencial | `server.replace` | ver matriz |
| `scripts/preview_worker_security_release_host.py:865` / `_restart_spec` | T | query/ORM | `policy.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:866` / `_restart_spec` | T | query/ORM | `policy.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:995` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:996` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:997` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:998` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:999` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1000` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:386` / `_record_file` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/preview_worker_security_release_host.py:532` / `verify_restored_runtime` | T | query/ORM | `current['services'].get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:613` / `_stop` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:618` / `_stop` | T | query/ORM | `current.get('State', {}).get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:686` / `stop_legacy_worker` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:761` / `_wait_healthy` | T | query/ORM | `value.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:764` / `_wait_healthy` | T | query/ORM | `state.get('Health', {}).get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:775` / `verify_candidate` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:803` / `verify_candidate` | T | query/ORM | `after['services'].get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:850` / `_assert_restart_policy` | T | query/ORM | `container.get('HostConfig', {}).get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1079` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1125` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1126` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:191` / `lock` | T | efeito potencial | `lock_path.open` | ver matriz |
| `scripts/preview_worker_security_release_host.py:594` / `verify_restored_runtime` | T | query/ORM | `curl_args.insert` | ver matriz |
| `scripts/preview_worker_security_release_host.py:625` / `_stop` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:641` / `pause_producers_for_recovery` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:644` / `pause_producers_for_recovery` | T | query/ORM | `current.get('State', {}).get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:694` / `stop_legacy_worker` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:695` / `stop_legacy_worker` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:696` / `stop_legacy_worker` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:762` / `_wait_healthy` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:834` / `resume_producers` | T | query/ORM | `self._container(service).get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:838` / `resume_producers` | T | query/ORM | `self._container(service)['State'].get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:852` / `_assert_restart_policy` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:853` / `_assert_restart_policy` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:857` / `_assert_restart_policy` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:858` / `_assert_restart_policy` | T | query/ORM | `actual.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:911` / `recover` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:916` / `recover` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:921` / `recover` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:944` / `recover` | T | query/ORM | `restored.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:968` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1002` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1014` / `recover_inflight` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1015` / `recover_inflight` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1016` / `recover_inflight` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1024` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1081` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1087` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1088` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1089` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1090` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1093` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1097` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1098` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1099` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1100` / `finish_journal` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1101` / `finish_journal` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:574` / `verify_restored_runtime` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:574` / `verify_restored_runtime` | T | query/ORM | `self.inventory_data.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:618` / `_stop` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:626` / `_stop` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:629` / `_stop` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:651` / `pause_producers_for_recovery` | T | query/ORM | `current.get('State', {}).get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:764` / `_wait_healthy` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:850` / `_assert_restart_policy` | T | query/ORM | `container.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:922` / `recover` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1004` / `recover_inflight` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:1141` / `finish_journal` | T | efeito potencial | `path.unlink` | ver matriz |
| `scripts/preview_worker_security_release_host.py:538` / `verify_restored_runtime` | T | query/ORM | `after.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:538` / `verify_restored_runtime` | T | query/ORM | `before.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:644` / `pause_producers_for_recovery` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:927` / `recover` | T | query/ORM | `self._inspect_id(current_id).get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:937` / `recover` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:541` / `verify_restored_runtime` | T | query/ORM | `after.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:541` / `verify_restored_runtime` | T | query/ORM | `before.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:651` / `pause_producers_for_recovery` | T | query/ORM | `current.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:805` / `verify_candidate` | T | query/ORM | `current_service.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:805` / `verify_candidate` | T | query/ORM | `before.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:928` / `recover` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:932` / `recover` | T | query/ORM | `state.get` | ver matriz |
| `scripts/preview_worker_security_release_host.py:929` / `recover` | T | query/ORM | `state.get` | ver matriz |
| `scripts/prove_preview_compose_preservation.py:38` / `main` | T | efeito potencial | `path.write_text` | ver matriz |
| `scripts/prove_preview_compose_preservation.py:43` / `main` | T | efeito potencial | `consolidated.write_text` | ver matriz |
| `scripts/prove_preview_compose_preservation.py:82` / `main` | T | efeito potencial | `consolidated.write_text` | ver matriz |
| `scripts/prove_preview_compose_preservation.py:18` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/prove_preview_compose_preservation.py:18` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/python_security_release.py:77` / `plan` | T | query/ORM | `services.get` | ver matriz |
| `scripts/python_security_release.py:89` / `plan` | T | query/ORM | `candidates.get` | ver matriz |
| `scripts/python_security_release.py:57` / `validate_candidate` | T | query/ORM | `candidate.get` | ver matriz |
| `scripts/python_security_release.py:66` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/python_security_release.py:67` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/python_security_release.py:68` / `plan` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/python_security_release.py:109` / `simulate` | T | query/ORM | `state.get` | ver matriz |
| `scripts/python_security_release.py:138` / `simulate` | T | query/ORM | `result['data'].update` | ver matriz |
| `scripts/python_security_release.py:176` / `main` | T | query/ORM | `inventory.get` | ver matriz |
| `scripts/python_security_release.py:90` / `plan` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/python_security_release.py:90` / `plan` | T | query/ORM | `proof.get` | ver matriz |
| `scripts/python_security_release.py:126` / `simulate` | T | query/ORM | `current.get` | ver matriz |
| `scripts/python_security_release.py:127` / `simulate` | T | query/ORM | `current.get` | ver matriz |
| `scripts/python_security_release.py:172` / `main` | T | query/ORM | `fixture.get` | ver matriz |
| `scripts/python_security_release.py:85` / `plan` | T | query/ORM | `item.get` | ver matriz |
| `scripts/reset_homolog_owner.py:94` / `require_schema` | T | query/ORM | `connection.get_execution_options().get('schema_translate_map', {}).get` | ver matriz |
| `scripts/reset_homolog_owner.py:107` / `foreign_keys` | T | query/ORM | `connection.get_execution_options().get('schema_translate_map', {}).get` | ver matriz |
| `scripts/reset_homolog_owner.py:128` / `owner_context` | T | query/ORM | `db.get` | ver matriz |
| `scripts/reset_homolog_owner.py:135` / `owner_context` | T | query/ORM | `db.get` | ver matriz |
| `scripts/reset_homolog_owner.py:150` / `policy` | T | query/ORM | `keep.update` | ver matriz |
| `scripts/reset_homolog_owner.py:151` / `policy` | T | query/ORM | `keep.update` | ver matriz |
| `scripts/reset_homolog_owner.py:160` / `policy` | T | query/ORM | `keep.update` | ver matriz |
| `scripts/reset_homolog_owner.py:320` / `execute` | T | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `scripts/reset_homolog_owner.py:338` / `execute` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/reset_homolog_owner.py:362` / `execute` | T | query/ORM | `result.update` | ver matriz |
| `scripts/reset_homolog_owner.py:122` / `owner_context` | T | query/ORM | `db.scalars` | ver matriz |
| `scripts/reset_homolog_owner.py:126` / `owner_context` | T | query/ORM | `db.scalars` | ver matriz |
| `scripts/reset_homolog_owner.py:127` / `owner_context` | T | query/ORM | `db.scalars` | ver matriz |
| `scripts/reset_homolog_owner.py:324` / `execute` | T | query/ORM | `schema_map.get` | ver matriz |
| `scripts/reset_homolog_owner.py:328` / `execute` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/reset_homolog_owner.py:340` / `execute` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/reset_homolog_owner.py:94` / `require_schema` | T | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `scripts/reset_homolog_owner.py:107` / `foreign_keys` | T | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `scripts/reset_homolog_owner.py:126` / `owner_context` | T | query/ORM | `select` | ver matriz |
| `scripts/reset_homolog_owner.py:141` / `owner_context` | T | query/ORM | `db.scalar` | ver matriz |
| `scripts/reset_homolog_owner.py:288` / `clear_root` | T | efeito potencial | `p.unlink` | ver matriz |
| `scripts/reset_homolog_owner.py:328` / `execute` | T | query/ORM | `text` | ver matriz |
| `scripts/reset_homolog_owner.py:338` / `execute` | T | query/ORM | `update` | ver matriz |
| `scripts/reset_homolog_owner.py:113` / `foreign_keys` | T | query/ORM | `fk.get` | ver matriz |
| `scripts/reset_homolog_owner.py:122` / `owner_context` | T | query/ORM | `select` | ver matriz |
| `scripts/reset_homolog_owner.py:127` / `owner_context` | T | query/ORM | `select` | ver matriz |
| `scripts/reset_homolog_owner.py:304` / `inventory` | T | query/ORM | `db.scalar` | ver matriz |
| `scripts/reset_homolog_owner.py:340` / `execute` | T | query/ORM | `delete` | ver matriz |
| `scripts/reset_homolog_owner.py:174` / `policy` | T | query/ORM | `select` | ver matriz |
| `scripts/reset_homolog_owner.py:182` / `preserved_rows` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/reset_homolog_owner.py:141` / `owner_context` | T | query/ORM | `select` | ver matriz |
| `scripts/reset_homolog_owner.py:182` / `preserved_rows` | T | query/ORM | `select` | ver matriz |
| `scripts/reset_homolog_owner.py:304` / `inventory` | T | query/ORM | `select` | ver matriz |
| `scripts/retirement_binding_removal.py:25` / `remove_binding` | T | query/ORM | `approved_inventory.get` | ver matriz |
| `scripts/retirement_binding_removal.py:26` / `remove_binding` | T | query/ORM | `approved.get` | ver matriz |
| `scripts/retirement_binding_removal.py:70` / `remove_binding` | T | efeito potencial | `os.unlink` | ver matriz |
| `scripts/retirement_financial_evidence.py:27` / `digest_rows` | T | query/ORM | `digest.update` | ver matriz |
| `scripts/retirement_financial_evidence.py:45` / `snapshot` | T | query/ORM | `connection.execute` | ver matriz |
| `scripts/retirement_financial_evidence.py:45` / `snapshot` | T | query/ORM | `text` | ver matriz |
| `scripts/retirement_host_references.py:52` / `find_references` | T | query/ORM | `visited_directories.add` | ver matriz |
| `scripts/retirement_host_references.py:92` / `find_container_references` | T | query/ORM | `mount.get` | ver matriz |
| `scripts/retirement_host_references.py:89` / `find_container_references` | T | query/ORM | `mount.get` | ver matriz |
| `scripts/retirement_pix_evidence.py:25` / `snapshot` | T | query/ORM | `db.scalars` | ver matriz |
| `scripts/retirement_pix_evidence.py:13` / `summarize` | T | query/ORM | `value.get` | ver matriz |
| `scripts/retirement_pix_evidence.py:14` / `summarize` | T | query/ORM | `value.get` | ver matriz |
| `scripts/retirement_pix_evidence.py:25` / `snapshot` | T | query/ORM | `select` | ver matriz |
| `scripts/retirement_pix_evidence.py:15` / `summarize` | T | query/ORM | `value.get` | ver matriz |
| `scripts/specialized_pillow_candidate.py:150` / `save` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/specialized_pillow_candidate.py:141` / `sync_directory` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/specialized_pillow_candidate.py:177` / `prepare` | T | efeito potencial | `(root / wheel['filename']).write_bytes` | ver matriz |
| `scripts/specialized_pillow_candidate.py:77` / `validate` | T | query/ORM | `before['packages'].get` | ver matriz |
| `scripts/specialized_pillow_candidate.py:192` / `prepare` | T | efeito potencial | `(root / 'Dockerfile').write_text` | ver matriz |
| `scripts/specialized_pillow_candidate.py:75` / `validate` | T | query/ORM | `base['Config'].get` | ver matriz |
| `scripts/specialized_pillow_candidate.py:75` / `validate` | T | query/ORM | `candidate['Config'].get` | ver matriz |
| `scripts/specialized_pillow_candidate.py:115` / `select_wheel` | T | query/ORM | `item.get` | ver matriz |
| `scripts/specialized_pillow_candidate.py:132` / `active` | T | query/ORM | `item['State'].get('Health', {}).get` | ver matriz |
| `scripts/specialized_pillow_candidate.py:132` / `active` | T | query/ORM | `item['State'].get` | ver matriz |
| `scripts/specialized_pillow_probe.py:85` / `probe` | T | efeito potencial | `Image.open` | ver matriz |
| `scripts/specialized_pillow_probe.py:35` / `probe` | T | efeito potencial | `Image.open` | ver matriz |
| `scripts/specialized_pillow_probe.py:64` / `probe` | T | efeito potencial | `Image.open` | ver matriz |
| `scripts/specialized_pillow_release.py:252` / `lock` | T | efeito potencial | `(STATE / 'production-release.lock').open` | ver matriz |
| `scripts/specialized_pillow_release.py:345` / `checkpoint` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/specialized_pillow_release.py:396` / `apply` | T | efeito potencial | `journal.unlink` | ver matriz |
| `scripts/specialized_pillow_release.py:57` / `configuration` | T | query/ORM | `config.get` | ver matriz |
| `scripts/specialized_pillow_release.py:160` / `projected_environment` | T | query/ORM | `projected[service].get` | ver matriz |
| `scripts/specialized_pillow_release.py:139` / `inventory` | T | query/ORM | `d['State'].get('Health', {}).get` | ver matriz |
| `scripts/specialized_pillow_release.py:173` / `guard` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/specialized_pillow_release.py:178` / `guard` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/specialized_pillow_release.py:220` / `healthy` | T | query/ORM | `d['State'].get('Health', {}).get` | ver matriz |
| `scripts/specialized_pillow_release.py:341` / `checkpoint` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/specialized_pillow_release.py:163` / `projected_environment` | T | query/ORM | `projected[service].get` | ver matriz |
| `scripts/specialized_pillow_release.py:58` / `configuration` | T | query/ORM | `item['Config'].get` | ver matriz |
| `scripts/specialized_pillow_release.py:139` / `inventory` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/specialized_pillow_release.py:159` / `projected_environment` | T | query/ORM | `d['Config'].get` | ver matriz |
| `scripts/specialized_pillow_release.py:220` / `healthy` | T | query/ORM | `d['State'].get` | ver matriz |
| `scripts/specialized_pillow_release.py:235` / `verify_ci` | T | query/ORM | `r.get` | ver matriz |
| `scripts/specialized_pillow_release.py:161` / `projected_environment` | T | query/ORM | `existing.get` | ver matriz |
| `scripts/third_party_report.py:224` / `_md` | T | efeito potencial | `text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('`', '&#96;').replace('[', '&#91;').replace` | ver matriz |
| `scripts/third_party_report.py:194` / `_priority` | T | query/ORM | `{'critical': 'P0', 'high': 'P1', 'moderate': 'P2', 'low': 'P3'}.get` | ver matriz |
| `scripts/third_party_report.py:323` / `build_report` | T | query/ORM | `current_versions.get` | ver matriz |
| `scripts/third_party_report.py:372` / `main` | T | efeito potencial | `args.output.write_text` | ver matriz |
| `scripts/third_party_report.py:224` / `_md` | T | efeito potencial | `text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('`', '&#96;').replace` | ver matriz |
| `scripts/third_party_report.py:275` / `build_report` | T | query/ORM | `package.get` | ver matriz |
| `scripts/third_party_report.py:276` / `build_report` | T | query/ORM | `package.get` | ver matriz |
| `scripts/third_party_report.py:277` / `build_report` | T | query/ORM | `advisory.get` | ver matriz |
| `scripts/third_party_report.py:278` / `build_report` | T | query/ORM | `vulnerability.get` | ver matriz |
| `scripts/third_party_report.py:280` / `build_report` | T | query/ORM | `patched.get` | ver matriz |
| `scripts/third_party_report.py:108` / `parse_release` | T | query/ORM | `value.get` | ver matriz |
| `scripts/third_party_report.py:271` / `build_report` | T | query/ORM | `alert.get` | ver matriz |
| `scripts/third_party_report.py:272` / `build_report` | T | query/ORM | `dependency.get` | ver matriz |
| `scripts/third_party_report.py:273` / `build_report` | T | query/ORM | `alert.get` | ver matriz |
| `scripts/third_party_report.py:274` / `build_report` | T | query/ORM | `alert.get` | ver matriz |
| `scripts/third_party_report.py:279` / `build_report` | T | query/ORM | `vulnerability.get` | ver matriz |
| `scripts/third_party_report.py:282` / `build_report` | T | query/ORM | `alert.get` | ver matriz |
| `scripts/third_party_report.py:299` / `build_report` | T | query/ORM | `pr.get` | ver matriz |
| `scripts/third_party_report.py:304` / `build_report` | T | query/ORM | `pr.get` | ver matriz |
| `scripts/third_party_report.py:80` / `fetch_json` | T | query/ORM | `error_body.get` | ver matriz |
| `scripts/third_party_report.py:172` / `parse_specialized_candidate` | T | query/ORM | `remote.get` | ver matriz |
| `scripts/third_party_report.py:224` / `_md` | T | efeito potencial | `text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace` | ver matriz |
| `scripts/third_party_report.py:224` / `_md` | T | efeito potencial | `text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace` | ver matriz |
| `scripts/third_party_report.py:224` / `_md` | T | efeito potencial | `text.replace('&', '&amp;').replace('<', '&lt;').replace` | ver matriz |
| `scripts/third_party_report.py:254` / `build_report` | T | query/ORM | `(item.get('user') or {}).get` | ver matriz |
| `scripts/third_party_report.py:224` / `_md` | T | efeito potencial | `text.replace('&', '&amp;').replace` | ver matriz |
| `scripts/third_party_report.py:254` / `build_report` | T | query/ORM | `item.get` | ver matriz |
| `scripts/third_party_report.py:224` / `_md` | T | efeito potencial | `text.replace` | ver matriz |
| `scripts/validate-homolog-public-origin.py:36` / `<módulo>` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/validate_retirement_approval.py:25` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/validate_retirement_approval.py:26` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:113` / `verify_remote` | T | query/ORM | `request_json(API + '/commits/main', token).get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:59` / `verify_jobs` | T | query/ORM | `indexed.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:121` / `verify_remote` | T | query/ORM | `request_json(API + '/commits/main', token).get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:48` / `select_run` | T | query/ORM | `latest.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:48` / `select_run` | T | query/ORM | `latest.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:56` / `verify_jobs` | T | query/ORM | `job.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:71` / `request_json` | T | efeito potencial | `build_opener(NoRedirect()).open` | ver matriz |
| `scripts/verify_main_ci_evidence.py:93` / `paginate` | T | query/ORM | `result.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:93` / `paginate` | T | query/ORM | `result.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:131` / `main` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:60` / `verify_jobs` | T | query/ORM | `matches[0].get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:60` / `verify_jobs` | T | query/ORM | `matches[0].get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:38` / `select_run` | T | query/ORM | `run.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:39` / `select_run` | T | query/ORM | `run.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:39` / `select_run` | T | query/ORM | `run.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:40` / `select_run` | T | query/ORM | `run.get` | ver matriz |
| `scripts/verify_main_ci_evidence.py:44` / `select_run` | T | query/ORM | `item.get` | ver matriz |
| `scripts/wildcard_certificate_custody.py:66` / `store` | T | efeito potencial | `self.cipher.encrypt` | ver matriz |
| `scripts/wildcard_certificate_custody.py:156` / `_point` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/wildcard_certificate_custody.py:48` / `private_write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_certificate_custody.py:152` / `_point` | T | efeito potencial | `link.unlink` | ver matriz |
| `scripts/wildcard_certificate_custody.py:164` / `install` | T | efeito potencial | `(self.root / '.install.lock').open` | ver matriz |
| `scripts/wildcard_certificate_custody.py:79` / `materialize` | T | efeito potencial | `self.cipher.decrypt` | ver matriz |
| `scripts/wildcard_certificate_custody.py:93` / `materialize` | T | efeito potencial | `path.unlink` | ver matriz |
| `scripts/wildcard_npm_lab.py:16` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/wildcard_npm_lab.py:67` / `run` | T | efeito potencial | `(root / '.pyp-wildcard-lab').write_text` | ver matriz |
| `scripts/wildcard_npm_lab.py:183` / `run` | T | efeito potencial | `Path('/tmp/pyp-wildcard-lab-result.json').write_text` | ver matriz |
| `scripts/wildcard_npm_lab.py:32` / `run` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/wildcard_npm_lab.py:101` / `probe_once` | T | efeito potencial | `secure.sendall` | ver matriz |
| `scripts/wildcard_npm_lab.py:50` / `run` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/wildcard_npm_lab.py:50` / `run` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/wildcard_npm_lab.py:174` / `run` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/wildcard_operational_custody.py:76` / `store` | T | efeito potencial | `self.cipher.encrypt` | ver matriz |
| `scripts/wildcard_operational_custody.py:104` / `materialize` | T | efeito potencial | `self.cipher.decrypt` | ver matriz |
| `scripts/wildcard_operational_custody.py:144` / `materialize` | T | efeito potencial | `os.unlink` | ver matriz |
| `scripts/wildcard_operational_files.py:18` / `_directory` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_operational_files.py:57` / `_read` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_operational_files.py:85` / `_write` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_operational_files.py:21` / `_directory` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:14` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:93` / `run` | T | efeito potencial | `update['advanced_config'].replace` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:155` / `run` | T | efeito potencial | `(helper / 'runtime-manifest.json').write_text` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:180` / `run` | T | efeito potencial | `(helper / 'trust.pem').write_bytes` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:113` / `run` | T | efeito potencial | `shutil.copyfile` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:26` / `run` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:42` / `run` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:39` / `run` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:204` / `run` | T | query/ORM | `db.execute` | ver matriz |
| `scripts/wildcard_operational_helper_lab.py:149` / `run` | T | efeito potencial | `target.open` | ver matriz |
| `scripts/wildcard_operational_installer.py:80` / `_journal` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/wildcard_operational_installer.py:124` / `_recover` | T | efeito potencial | `os.unlink` | ver matriz |
| `scripts/wildcard_operational_installer.py:67` / `_point` | T | efeito potencial | `os.replace` | ver matriz |
| `scripts/wildcard_operational_installer.py:72` / `_journal` | T | efeito potencial | `os.unlink` | ver matriz |
| `scripts/wildcard_operational_installer.py:133` / `install` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_operational_installer.py:185` / `install` | T | efeito potencial | `os.unlink` | ver matriz |
| `scripts/wildcard_operational_installer.py:57` / `_point` | T | efeito potencial | `os.unlink` | ver matriz |
| `scripts/wildcard_operational_installer.py:63` / `_point` | T | efeito potencial | `os.unlink` | ver matriz |
| `scripts/wildcard_operational_issuer.py:57` / `issue` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_operational_npm_helper.py:13` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/wildcard_operational_npm_helper.py:64` / `tls` | T | efeito potencial | `secure.sendall` | ver matriz |
| `scripts/wildcard_operational_npm_lab.py:6` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/wildcard_operational_package_manifest.py:13` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/wildcard_operational_package_manifest.py:183` / `main` | T | efeito potencial | `OUTPUT.write_text` | ver matriz |
| `scripts/wildcard_operational_package_manifest.py:47` / `sha256` | T | efeito potencial | `path.open` | ver matriz |
| `scripts/wildcard_operational_package_manifest.py:49` / `sha256` | T | query/ORM | `digest.update` | ver matriz |
| `scripts/wildcard_operational_protocol.py:103` / `handle_connection` | T | efeito potencial | `connection.sendall` | ver matriz |
| `scripts/wildcard_operational_runtime.py:52` / `load_runtime` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/wildcard_operational_runtime.py:40` / `load_runtime` | T | query/ORM | `actual.add` | ver matriz |
| `scripts/wildcard_operational_service.py:16` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/wildcard_operational_service.py:43` / `root_public_file` | T | efeito potencial | `os.open` | ver matriz |
| `scripts/wildcard_operational_service.py:121` / `issuer_once` | T | efeito potencial | `client.sendall` | ver matriz |
| `scripts/wildcard_operational_service.py:130` / `issuer_once` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/wildcard_operational_service.py:130` / `issuer_once` | T | query/ORM | `receipt.get` | ver matriz |
| `scripts/wildcard_operational_service.py:141` / `helper` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/wildcard_operational_service.py:142` / `helper` | T | query/ORM | `os.environ.get` | ver matriz |
| `scripts/wildcard_systemd_guest.py:44` / `record_phase` | T | efeito potencial | `phase.write_text` | ver matriz |
| `scripts/wildcard_systemd_guest.py:140` / `worker` | T | efeito potencial | `receipt_path.write_text` | ver matriz |
| `scripts/wildcard_systemd_guest.py:194` / `prepare` | T | efeito potencial | `key.write_bytes` | ver matriz |
| `scripts/wildcard_systemd_guest.py:237` / `prepare` | T | efeito potencial | `Path('/etc/systemd/system/' + UNIT).write_text` | ver matriz |
| `scripts/wildcard_systemd_guest.py:248` / `prepare` | T | efeito potencial | `Path('/var/lib/pyp-first-boot-id').write_text` | ver matriz |
| `scripts/wildcard_systemd_guest.py:261` / `prepare` | T | efeito potencial | `Path('/etc/systemd/system/pyp-wildcard-finish.service').write_text` | ver matriz |
| `scripts/wildcard_systemd_guest.py:291` / `finish` | T | query/ORM | `result.update` | ver matriz |
| `scripts/wildcard_systemd_guest.py:316` / `verify_logs_and_mark` | T | efeito potencial | `receipt_path.write_text` | ver matriz |
| `scripts/wildcard_systemd_guest.py:213` / `prepare` | T | efeito potencial | `target.open` | ver matriz |
| `scripts/wildcard_systemd_vm.py:39` / `run` | T | efeito potencial | `(work / 'user-data').write_text` | ver matriz |
| `scripts/wildcard_systemd_vm.py:40` / `run` | T | efeito potencial | `(work / 'meta-data').write_text` | ver matriz |
| `scripts/wildcard_systemd_vm.py:41` / `run` | T | efeito potencial | `(work / 'network-config').write_text` | ver matriz |
| `scripts/wildcard_systemd_vm.py:10` / `run` | T | query/ORM | `os.environ.get` | ver matriz |

## Cache estado local e wake-up

| Fonte | Critério/teste | Sinal |
| --- | --- | --- |
| `backend/app/capacity_observability/collector.py:37` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:41` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:42` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:197` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:208` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:209` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:213` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:214` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:217` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:227` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:228` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:231` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:235` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:236` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:237` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/collector.py:238` | O | armazenamento/cache/wake-up |
| `backend/app/capacity_observability/contracts.py:147` | O | armazenamento/cache/wake-up |
| `backend/app/environment_transition_inventory.py:73` | X | armazenamento/cache/wake-up |
| `backend/app/environment_transition_inventory.py:81` | X | armazenamento/cache/wake-up |
| `backend/app/facial/face_worker.py:11` | F | armazenamento/cache/wake-up |
| `backend/app/facial/face_worker.py:36` | F | armazenamento/cache/wake-up |
| `backend/app/facial/face_worker.py:167` | F | armazenamento/cache/wake-up |
| `backend/app/facial/face_worker.py:168` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:1` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:66` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:403` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:416` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:109` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:111` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:134` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:136` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:159` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:22` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:70` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:75` | F | armazenamento/cache/wake-up |
| `backend/app/google_drive_oauth.py:48` | A | armazenamento/cache/wake-up |
| `backend/app/installation_operator.py:13` | O | armazenamento/cache/wake-up |
| `backend/app/main.py:512` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:528` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1258` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1406` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1413` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1446` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2263` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2264` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2604` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2878` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3022` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3027` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3038` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3195` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3237` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3256` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3264` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3281` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3285` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3344` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3362` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3366` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3383` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3387` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3432` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3440` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3451` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3464` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3476` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3491` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3511` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3522` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3532` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3550` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3578` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3784` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3794` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:3795` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:7972` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:8014` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:8102` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:8126` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:11664` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:13886` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:14114` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:14289` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:14439` | X | armazenamento/cache/wake-up |
| `backend/app/mercadopago_api.py:63` | S | armazenamento/cache/wake-up |
| `backend/app/mercadopago_checkout.py:352` | S | armazenamento/cache/wake-up |
| `backend/app/photographer_access_recovery.py:55` | A | armazenamento/cache/wake-up |
| `backend/app/photographer_credits.py:72` | S | armazenamento/cache/wake-up |
| `backend/app/photographer_onboarding.py:265` | A | armazenamento/cache/wake-up |
| `backend/app/photographer_onboarding.py:276` | A | armazenamento/cache/wake-up |
| `backend/app/photographer_onboarding.py:487` | A | armazenamento/cache/wake-up |
| `backend/app/photographer_signup.py:55` | A | armazenamento/cache/wake-up |
| `backend/app/photographer_subdomain.py:17` | X | armazenamento/cache/wake-up |
| `backend/app/photographer_terms.py:33` | A | armazenamento/cache/wake-up |
| `backend/app/photographer_totp.py:45` | A | armazenamento/cache/wake-up |
| `backend/app/platform_console.py:38` | A | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:22` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:23` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:32` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:33` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:37` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:43` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:46` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:48` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:49` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:50` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:51` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:88` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:90` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:92` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:93` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:95` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:96` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:97` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:99` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:109` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:110` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:171` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:179` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:180` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:182` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:183` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:184` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:185` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:186` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:190` | X | armazenamento/cache/wake-up |
| `backend/app/system_monitor/access.py:20` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/routes.py:1` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/routes.py:21` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/storage.py:11` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/storage.py:16` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/storage.py:17` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/storage.py:18` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/storage.py:47` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/storage.py:52` | O | armazenamento/cache/wake-up |
| `backend/app/system_monitor/telemetry.py:137` | O | armazenamento/cache/wake-up |
| `backend/app/tenant_closure_api.py:30` | L | armazenamento/cache/wake-up |
| `backend/app/tenant_closure_identity.py:45` | L | armazenamento/cache/wake-up |
| `scripts/build_python_security_candidates.py:112` | T | armazenamento/cache/wake-up |
| `scripts/deploy-homolog.sh:746` | T | armazenamento/cache/wake-up |
| `scripts/deploy-homolog.sh:748` | T | armazenamento/cache/wake-up |
| `scripts/environment_cutover_release.py:36` | T | armazenamento/cache/wake-up |
| `scripts/environment_cutover_release.py:37` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:28` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:47` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:49` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:88` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:91` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:113` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:116` | T | armazenamento/cache/wake-up |
| `scripts/facial_runtime_candidate.py:343` | T | armazenamento/cache/wake-up |
| `scripts/facial_runtime_restoration.py:23` | T | armazenamento/cache/wake-up |
| `scripts/facial_runtime_restoration_host.py:46` | T | armazenamento/cache/wake-up |
| `scripts/inventory-homolog-readonly.sh:67` | T | armazenamento/cache/wake-up |
| `scripts/inventory-homolog-readonly.sh:107` | T | armazenamento/cache/wake-up |
| `scripts/inventory-homolog-readonly.sh:109` | T | armazenamento/cache/wake-up |
| `scripts/local_photographer_demo.py:231` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:76` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:92` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:119` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:170` | T | armazenamento/cache/wake-up |
| `scripts/orders_pilot_release.py:66` | T | armazenamento/cache/wake-up |
| `scripts/orders_pilot_release.py:725` | T | armazenamento/cache/wake-up |
| `scripts/orders_pilot_release.py:951` | T | armazenamento/cache/wake-up |
| `scripts/prepare_emergency_api_image.py:128` | T | armazenamento/cache/wake-up |
| `scripts/preview_adjustment_migration_inventory.py:31` | T | armazenamento/cache/wake-up |
| `scripts/preview_adjustment_migration_inventory.py:33` | T | armazenamento/cache/wake-up |
| `scripts/preview_worker_maintenance_flow.py:4` | T | armazenamento/cache/wake-up |
| `scripts/preview_worker_security_inventory.py:27` | T | armazenamento/cache/wake-up |
| `scripts/preview_worker_security_inventory.py:33` | T | armazenamento/cache/wake-up |
| `scripts/preview_worker_security_inventory.py:47` | T | armazenamento/cache/wake-up |
| `scripts/preview_worker_security_release_host.py:263` | T | armazenamento/cache/wake-up |
| `scripts/reset-homolog-owner.sh:36` | T | armazenamento/cache/wake-up |
| `scripts/reset-homolog-owner.sh:97` | T | armazenamento/cache/wake-up |
| `scripts/reset-homolog-owner.sh:120` | T | armazenamento/cache/wake-up |
| `scripts/reset-homolog-owner.sh:241` | T | armazenamento/cache/wake-up |
| `scripts/reset-homolog-owner.sh:243` | T | armazenamento/cache/wake-up |
| `scripts/resume-homolog.sh:172` | T | armazenamento/cache/wake-up |
| `scripts/retirement_inventory_policy.py:62` | T | armazenamento/cache/wake-up |
| `scripts/retirement_inventory_policy.py:64` | T | armazenamento/cache/wake-up |
| `scripts/specialized_pillow_candidate.py:43` | T | armazenamento/cache/wake-up |
| `scripts/specialized_pillow_candidate.py:190` | T | armazenamento/cache/wake-up |
| `scripts/specialized_pillow_release.py:39` | T | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:45` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:78` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:128` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:137` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-report.ts:57` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-report.ts:117` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/credit-history.tsx:43` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/credit-purchase-checkout.tsx:101` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/credit-upload-status.tsx:87` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/credit-upload-status.tsx:121` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/media-archive-recovery-panel.tsx:114` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/media-archive-recovery-panel.tsx:117` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/media-archive-recovery-panel.tsx:120` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/media-archive-recovery-panel.tsx:181` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/media-archive-recovery-panel.tsx:216` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-credit-operations.tsx:175` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-credit-operations.tsx:207` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-credit-operations.tsx:236` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-credit-operations.tsx:327` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-credit-operations.tsx:399` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-credit-operations.tsx:447` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-credit-operations.tsx:497` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/owner-media-archive-recoveries.tsx:86` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:117` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:136` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:153` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:171` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:174` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:204` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:239` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/credits/page.tsx:326` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:80` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:424` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:453` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-deadline-fields.tsx:28` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:45` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:62` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:207` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:219` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/private-folder-client-overview.tsx:26` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:119` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:397` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:410` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:999` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:1041` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/installation-diagnostics.tsx:27` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/notifications/media-archive-notice-center.tsx:52` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/notifications/media-archive-notice-center.tsx:72` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/notifications/page.tsx:85` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/page.tsx:122` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:210` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:211` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:390` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:396` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:404` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:405` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:406` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:617` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/payments/page.tsx:631` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/page.tsx:104` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/page.tsx:122` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/photographer-access-recovery.tsx:33` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/photographer-access-recovery.tsx:51` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/photographer-terms-editor.tsx:17` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/photographer-terms-history.tsx:24` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/photographer-totp-support.tsx:33` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/photographer-totp-support.tsx:62` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/tenant-closure-console.tsx:223` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/tenant-closure-console.tsx:242` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/tenant-closure-console.tsx:265` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/platform/use-console-access.ts:19` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/onboarding-panel.tsx:63` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/onboarding-panel.tsx:68` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/onboarding-panel.tsx:78` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/onboarding-panel.tsx:84` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/onboarding-panel.tsx:119` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/page.tsx:407` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/photographer-totp-setup.tsx:36` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/photographer-totp-setup.tsx:56` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/tenant-closure-panel.tsx:27` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/tenant-closure-panel.tsx:42` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/tenant-closure-panel.tsx:66` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:77` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:131` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:228` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/page.tsx:52` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/page.tsx:70` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/page.tsx:94` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/page.tsx:96` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/page.tsx:105` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/use-permissions.ts:23` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/user-tree.tsx:19` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/user-tree.tsx:28` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/user-tree.tsx:37` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/system-monitor/user-tree.tsx:50` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/tenant-address.ts:39` | U | armazenamento/cache/wake-up |
| `frontend/app/admin-session-toolbar.tsx:18` | U | armazenamento/cache/wake-up |
| `frontend/app/auth-entry.tsx:81` | U | armazenamento/cache/wake-up |
| `frontend/app/authenticated-identity.tsx:16` | U | armazenamento/cache/wake-up |
| `frontend/app/client-navigation.tsx:18` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-client.ts:83` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:7` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:9` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:20` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:26` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:27` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:90` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:100` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:131` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:142` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:169` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:174` | U | armazenamento/cache/wake-up |
| `frontend/app/install-app.tsx:45` | U | armazenamento/cache/wake-up |
| `frontend/app/library/cart/page.tsx:39` | U | armazenamento/cache/wake-up |
| `frontend/app/library/mercadopago.ts:42` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:63` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:98` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:104` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:105` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:106` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchases/page.tsx:34` | U | armazenamento/cache/wake-up |
| `frontend/app/monitor-activity.tsx:17` | U | armazenamento/cache/wake-up |
| `frontend/app/monitor-activity.tsx:25` | U | armazenamento/cache/wake-up |
| `frontend/app/photographer-signup/page.tsx:13` | U | armazenamento/cache/wake-up |
| `frontend/app/public-galleries/[galleryId]/page.tsx:94` | U | armazenamento/cache/wake-up |
| `frontend/app/push-control.tsx:9` | U | armazenamento/cache/wake-up |
| `frontend/app/push-control.tsx:21` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:12` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:19` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:38` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:49` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:66` | U | armazenamento/cache/wake-up |
| `frontend/app/session-boundary.tsx:17` | U | armazenamento/cache/wake-up |
| `frontend/app/session-boundary.tsx:78` | U | armazenamento/cache/wake-up |
| `frontend/app/session-boundary.tsx:85` | U | armazenamento/cache/wake-up |
| `frontend/app/theme-control.tsx:34` | U | armazenamento/cache/wake-up |
| `frontend/app/theme-control.tsx:35` | U | armazenamento/cache/wake-up |
| `frontend/app/theme.ts:11` | U | armazenamento/cache/wake-up |
| `frontend/app/theme.ts:28` | U | armazenamento/cache/wake-up |
| `frontend/app/theme.ts:39` | U | armazenamento/cache/wake-up |
| `frontend/app/upload-jpeg.ts:78` | U | armazenamento/cache/wake-up |
| `frontend/public/markina-sw.js:1` | U | armazenamento/cache/wake-up |
| `frontend/public/markina-sw.js:53` | U | armazenamento/cache/wake-up |
