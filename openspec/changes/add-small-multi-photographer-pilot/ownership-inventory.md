# Inventário de código — complemento da matriz

Gerado por `inventory_ownership.py`; consultar `ownership-matrix.md` para decisões, critérios A–X, testes e limites. Este inventário estático associa fontes a critérios; não executa testes nem decide prontidão. O estado e as evidências de implementação/validação estão na matriz e em `validation.md`.

SHA256 das fontes inventariadas: `d4bbf8c0ced09ea3c8283086062565981d699c84e4390ddebdad61f090055a4b`.

Contagens: arquivos=247; efeito potencial=236; estado=178; gate=691; produtor=149; query/ORM=2690; rotas=259; sitios=3765; tabelas=93.

## Tabelas

| Tabela/modelo | Classe | Critério/teste | Fonte | FKs atuais | Evidência por critério |
| --- | --- | --- | --- | --- | --- |
| `branding_settings` / `BrandingSettings` | R | K | `backend/app/auth.py:101` | tenant.id | ver matriz |
| `admin_user` / `AdminUser` | I | A | `backend/app/auth.py:144` | sem FK | ver matriz |
| `installation_operator` / `InstallationOperator` | I | O | `backend/app/auth.py:154` | admin_user.id | ver matriz |
| `facial_embedding_experiment_setting` / `FacialEmbeddingExperimentSetting` | I | O | `backend/app/auth.py:169` | admin_user.id | ver matriz |
| `tenant` / `Tenant` | I | A | `backend/app/auth.py:195` | sem FK | ver matriz |
| `tenant_admin` / `TenantAdmin` | D | A | `backend/app/auth.py:205` | admin_user.id; tenant.id | ver matriz |
| `admin_security_challenge` / `AdminSecurityChallenge` | M | A | `backend/app/auth.py:215` | admin_user.id; tenant.id | ver matriz |
| `admin_action_token` / `AdminActionToken` | I | A | `backend/app/auth.py:248` | admin_user.id | ver matriz |
| `email_delivery` / `EmailDelivery` | I | A | `backend/app/auth.py:264` | sem FK | ver matriz |
| `email_delivery_attempt` / `EmailDeliveryAttempt` | I | A | `backend/app/auth.py:297` | email_delivery.id | ver matriz |
| `client` / `Client` | R | C | `backend/app/auth.py:314` | tenant.id | ver matriz |
| `client_phone` / `ClientPhone` | D | C | `backend/app/auth.py:326` | client.id; tenant.id; composta:fk_client_phone_client_tenant | ver matriz |
| `client_deletion_receipt` / `ClientDeletionReceipt` | R | C | `backend/app/auth.py:364` | admin_user.id; tenant.id | ver matriz |
| `gallery_access` / `GalleryAccess` | R | G | `backend/app/auth.py:399` | client.id; derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `parent_gallery` / `ParentGallery` | R | G | `backend/app/auth.py:425` | photo_asset.id; progressive_pricing_preset.id; tenant.id | ver matriz |
| `parent_gallery_registration` / `ParentGalleryRegistration` | D | G | `backend/app/auth.py:496` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `photo_asset` / `PhotoAsset` | R | G | `backend/app/auth.py:512` | derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_photo_asset_folder_gallery; composta:fk_photo_asset_folder_scope; composta:fk_photo_asset_parent_tenant; composta:fk_photo_asset_private_tenant | ver matriz |
| `photo_folder` / `PhotoFolder` | D | G | `backend/app/auth.py:558` | derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `gallery_client_state` / `GalleryClientState` | D | G | `backend/app/auth.py:622` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `folder_client_grant` / `FolderClientGrant` | D | G | `backend/app/auth.py:648` | tenant.id; composta:fk_folder_client_grant_client_state; composta:fk_folder_client_grant_folder_parent | ver matriz |
| `derived_gallery` / `DerivedGallery` | R | G | `backend/app/auth.py:678` | client.id; parent_gallery.id; tenant.id; composta:fk_derived_gallery_parent_tenant | ver matriz |
| `derived_gallery_membership` / `DerivedGalleryMembership` | D | G | `backend/app/auth.py:716` | admin_user.id; client.id; parent_gallery.id; tenant.id; composta:fk_membership_gallery_parent | ver matriz |
| `derived_gallery_photo` / `DerivedGalleryPhoto` | D | G | `backend/app/auth.py:769` | derived_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `derived_gallery_photo_origin` / `DerivedGalleryPhotoOrigin` | D | G | `backend/app/auth.py:795` | derived_gallery_photo.id; tenant.id | ver matriz |
| `photo_selection` / `PhotoSelection` | D | S | `backend/app/auth.py:823` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_favorite` / `PhotoFavorite` | D | S | `backend/app/auth.py:857` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_view` / `PhotoView` | D | S | `backend/app/auth.py:890` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_comment` / `PhotoComment` | D | S | `backend/app/auth.py:923` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `payment_group` / `PaymentGroup` | R | S | `backend/app/auth.py:950` | client.id; tenant.id | ver matriz |
| `provider_payment` / `ProviderPayment` | R | S | `backend/app/auth.py:978` | client.id; tenant.id | ver matriz |
| `provider_payment_attempt` / `ProviderPaymentAttempt` | D | S | `backend/app/auth.py:1013` | client.id; tenant.id; composta:fk_provider_attempt_payment_owner | ver matriz |
| `provider_payment_receipt` / `ProviderPaymentReceipt` | D | S | `backend/app/auth.py:1035` | client.id; tenant.id; composta:fk_provider_receipt_payment_owner | ver matriz |
| `provider_payment_correction` / `ProviderPaymentCorrection` | D | S | `backend/app/auth.py:1062` | admin_user.id; client.id; tenant.id; composta:fk_provider_correction_payment_owner | ver matriz |
| `sale_order` / `SaleOrder` | R | S | `backend/app/auth.py:1087` | client.id; derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_sale_order_canonical_state; composta:fk_sale_order_payment_group_owner; composta:fk_sale_order_provider_payment_owner | ver matriz |
| `sale_order_item` / `SaleOrderItem` | D | S | `backend/app/auth.py:1196` | photo_asset.id; sale_order.id; tenant.id | ver matriz |
| `removed_photo_movement` / `RemovedPhotoMovement` | R | S | `backend/app/auth.py:1219` | client.id; tenant.id | ver matriz |
| `asset_file_cleanup` / `AssetFileCleanup` | R | L | `backend/app/auth.py:1242` | tenant.id | ver matriz |
| `gallery_lifecycle_operation` / `GalleryLifecycleOperation` | R | L | `backend/app/auth.py:1258` | tenant.id | ver matriz |
| `gallery_access_capability` / `GalleryAccessCapability` | D | G | `backend/app/auth.py:1311` | client.id; derived_gallery.id; gallery_access_capability.id; parent_gallery.id; tenant.id | ver matriz |
| `commercial_history_media` / `CommercialHistoryMedia` | R | S | `backend/app/auth.py:1406` | sale_order_item.id; tenant.id | ver matriz |
| `price_rule` / `PriceRule` | D | K | `backend/app/auth.py:1516` | parent_gallery.id; tenant.id | ver matriz |
| `pix_checkout_settings` / `PixCheckoutSettings` | D | K | `backend/app/auth.py:1537` | parent_gallery.id; tenant.id | ver matriz |
| `infinitepay_settings` / `InfinitePaySettings` | R | K | `backend/app/auth.py:1563` | admin_user.id; tenant.id | ver matriz |
| `global_pix_settings` / `GlobalPixSettings` | R | K | `backend/app/auth.py:1592` | admin_user.id; tenant.id | ver matriz |
| `payment_communication` / `PaymentCommunication` | D | S | `backend/app/auth.py:1621` | admin_user.id; client.id; sale_order.id; tenant.id; composta:fk_payment_communication_group_owner | ver matriz |
| `payment_confirmation_correction` / `PaymentConfirmationCorrection` | D | S | `backend/app/auth.py:1646` | admin_user.id; payment_communication.id; sale_order.id; tenant.id | ver matriz |
| `payment_message_template` / `PaymentMessageTemplate` | R | K | `backend/app/auth.py:1682` | tenant.id | ver matriz |
| `payment_notification_outbox` / `PaymentNotificationOutbox` | D | N | `backend/app/auth.py:1694` | payment_communication.id; tenant.id | ver matriz |
| `gallery_reopening_request` / `GalleryReopeningRequest` | D | S | `backend/app/auth.py:1720` | admin_user.id; client.id; derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_gallery_reopening_canonical_state | ver matriz |
| `gallery_reopening_notification_outbox` / `GalleryReopeningNotificationOutbox` | D | N | `backend/app/auth.py:1793` | gallery_reopening_request.id; tenant.id | ver matriz |
| `progressive_pricing_preset` / `ProgressivePricingPreset` | R | K | `backend/app/auth.py:1825` | tenant.id | ver matriz |
| `progressive_pricing_tier` / `ProgressivePricingTier` | D | K | `backend/app/auth.py:1846` | progressive_pricing_preset.id; tenant.id | ver matriz |
| `gallery_membership_notification_outbox` / `GalleryMembershipNotificationOutbox` | R | N | `backend/app/auth.py:1875` | client.id; derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `whatsapp_channel_settings` / `WhatsAppChannelSettings` | R | K | `backend/app/auth.py:1941` | tenant.id | ver matriz |
| `whatsapp_delivery` / `WhatsAppDelivery` | R | N | `backend/app/auth.py:1965` | tenant.id | ver matriz |
| `whatsapp_delivery_attempt` / `WhatsAppDeliveryAttempt` | D | N | `backend/app/auth.py:2009` | tenant.id; whatsapp_delivery.id | ver matriz |
| `whatsapp_webhook_receipt` / `WhatsAppWebhookReceipt` | R | N | `backend/app/auth.py:2029` | tenant.id | ver matriz |
| `media_derivative` / `MediaDerivative` | D | P | `backend/app/auth.py:2042` | photo_asset.id; tenant.id | ver matriz |
| `media_job` / `MediaJob` | R | P | `backend/app/auth.py:2066` | photo_asset.id; tenant.id | ver matriz |
| `preview_adjustment_settings` / `PreviewAdjustmentSettings` | R | K | `backend/app/auth.py:2090` | tenant.id | ver matriz |
| `gallery_preview_settings` / `GalleryPreviewSettings` | D | K | `backend/app/auth.py:2109` | parent_gallery.id; tenant.id | ver matriz |
| `folder_processing_settings` / `FolderProcessingSettings` | D | K | `backend/app/auth.py:2131` | photo_folder.id; tenant.id | ver matriz |
| `preview_adjustment` / `PreviewAdjustment` | D | P | `backend/app/auth.py:2156` | photo_asset.id; tenant.id | ver matriz |
| `gallery_facial_policy` / `GalleryFacialPolicy` | D | F | `backend/app/auth.py:2182` | admin_user.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_rollout` / `FacialRollout` | D | F | `backend/app/auth.py:2227` | admin_user.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_calibration_approval` / `FacialCalibrationApproval` | R | F | `backend/app/auth.py:2296` | admin_user.id; tenant.id | ver matriz |
| `facial_rollout_operation` / `FacialRolloutOperation` | R | F | `backend/app/auth.py:2355` | admin_user.id; tenant.id | ver matriz |
| `facial_legal_representation` / `FacialLegalRepresentation` | D | F | `backend/app/auth.py:2399` | admin_user.id; client.id; parent_gallery.id; tenant.id | ver matriz |
| `photo_analysis` / `PhotoAnalysis` | D | F | `backend/app/auth.py:2458` | photo_asset.id; tenant.id | ver matriz |
| `photo_face_embedding` / `PhotoFaceEmbedding` | D | F | `backend/app/auth.py:2487` | derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_face_embedding_photo_parent | ver matriz |
| `facial_search_request` / `FacialSearchRequest` | R | F | `backend/app/auth.py:2566` | client.id; gallery_facial_policy.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_search_snapshot_item` / `FacialSearchSnapshotItem` | D | F | `backend/app/auth.py:2653` | tenant.id; composta:fk_facial_snapshot_photo_parent; composta:fk_facial_snapshot_search_scope | ver matriz |
| `facial_search_candidate` / `FacialSearchCandidate` | D | F | `backend/app/auth.py:2700` | tenant.id; composta:fk_facial_candidate_photo_parent; composta:fk_facial_candidate_search_scope | ver matriz |
| `facial_job` / `FacialJob` | R | F | `backend/app/auth.py:2745` | derived_gallery.id; facial_search_request.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `facial_search_notification_outbox` / `FacialSearchNotificationOutbox` | D | F | `backend/app/auth.py:2805` | tenant.id; composta:fk_facial_notification_search_scope | ver matriz |
| `auth_challenge` / `AuthChallenge` | M | A | `backend/app/auth.py:2860` | tenant.id | ver matriz |
| `notification_setting` / `NotificationSetting` | R | K | `backend/app/auth.py:2884` | tenant.id | ver matriz |
| `notification_milestone` / `NotificationMilestone` | D | N | `backend/app/auth.py:2902` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `push_subscription` / `PushSubscription` | R | N | `backend/app/auth.py:2920` | admin_user.id; auth_session.id; client.id; tenant.id | ver matriz |
| `notification_event` / `NotificationEvent` | R | N | `backend/app/auth.py:2955` | client.id; derived_gallery.id; parent_gallery.id; sale_order.id; tenant.id | ver matriz |
| `notification_delivery` / `NotificationDelivery` | D | N | `backend/app/auth.py:2984` | admin_user.id; client.id; notification_event.id; push_subscription.id; tenant.id | ver matriz |
| `private_upload_batch` / `PrivateUploadBatch` | D | G | `backend/app/auth.py:3029` | admin_user.id; derived_gallery.id; tenant.id | ver matriz |
| `private_upload_batch_asset` / `PrivateUploadBatchAsset` | D | G | `backend/app/auth.py:3047` | photo_asset.id; private_upload_batch.id; tenant.id | ver matriz |
| `auth_session` / `AuthSession` | M | A | `backend/app/auth.py:3060` | admin_user.id; client.id; tenant.id | ver matriz |
| `audit_event` / `AuditEvent` | M | A | `backend/app/auth.py:3086` | tenant.id | ver matriz |
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
| `backend/app/commercial_history.py` | S | ver matriz |
| `backend/app/commercial_projection.py` | S | ver matriz |
| `backend/app/commercial_removal.py` | L | ver matriz |
| `backend/app/commercial_retention.py` | L | ver matriz |
| `backend/app/email_delivery.py` | N | ver matriz |
| `backend/app/facial/__init__.py` | F | ver matriz |
| `backend/app/facial/analysis_metrics.py` | F | ver matriz |
| `backend/app/facial/calibration.py` | F | ver matriz |
| `backend/app/facial/capacity.py` | F | ver matriz |
| `backend/app/facial/config.py` | F | ver matriz |
| `backend/app/facial/crypto.py` | F | ver matriz |
| `backend/app/facial/detection.py` | F | ver matriz |
| `backend/app/facial/engine.py` | F | ver matriz |
| `backend/app/facial/face_worker.py` | F | ver matriz |
| `backend/app/facial/gemma_assets.py` | F | ver matriz |
| `backend/app/facial/gemma_provider.py` | F | ver matriz |
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
| `backend/app/folder_processing.py` | P | ver matriz |
| `backend/app/folder_processing_api.py` | P | ver matriz |
| `backend/app/gallery_access.py` | G | ver matriz |
| `backend/app/gallery_cleanup.py` | L | ver matriz |
| `backend/app/gallery_cover_readiness.py` | G | ver matriz |
| `backend/app/gallery_lifecycle.py` | L | ver matriz |
| `backend/app/gallery_pricing.py` | K | ver matriz |
| `backend/app/gallery_visuals.py` | G | ver matriz |
| `backend/app/global_pix.py` | K | ver matriz |
| `backend/app/historical_media.py` | X | ver matriz |
| `backend/app/homolog_cleanup.py` | L | ver matriz |
| `backend/app/infinitepay_settings.py` | K | ver matriz |
| `backend/app/installation_operator.py` | O | ver matriz |
| `backend/app/main.py` | X | ver matriz |
| `backend/app/media.py` | P | ver matriz |
| `backend/app/membership_notifications.py` | N | ver matriz |
| `backend/app/messaging.py` | N | ver matriz |
| `backend/app/notification_contract.py` | N | ver matriz |
| `backend/app/notification_delivery.py` | N | ver matriz |
| `backend/app/notification_events.py` | N | ver matriz |
| `backend/app/notification_settings.py` | K | ver matriz |
| `backend/app/order_delivery.py` | S | ver matriz |
| `backend/app/ownership_schema.py` | X | ver matriz |
| `backend/app/parent_registration.py` | G | ver matriz |
| `backend/app/payment_provider.py` | K | ver matriz |
| `backend/app/payment_templates.py` | K | ver matriz |
| `backend/app/pix.py` | S | ver matriz |
| `backend/app/preview_adjustment/__init__.py` | P | ver matriz |
| `backend/app/preview_adjustment/api.py` | P | ver matriz |
| `backend/app/preview_adjustment/cleanup.py` | P | ver matriz |
| `backend/app/preview_adjustment/engine.py` | P | ver matriz |
| `backend/app/preview_adjustment/service.py` | P | ver matriz |
| `backend/app/preview_adjustment/worker.py` | P | ver matriz |
| `backend/app/pricing.py` | S | ver matriz |
| `backend/app/private_derivation.py` | G | ver matriz |
| `backend/app/private_gallery_lifecycle.py` | L | ver matriz |
| `backend/app/private_membership.py` | G | ver matriz |
| `backend/app/private_upload_batches.py` | G | ver matriz |
| `backend/app/product_brand.py` | I | ver matriz |
| `backend/app/provider_checkout.py` | S | ver matriz |
| `backend/app/provider_confirmation.py` | S | ver matriz |
| `backend/app/provision_installation_operator.py` | O | ver matriz |
| `backend/app/provision_photographer.py` | A | ver matriz |
| `backend/app/public_gallery_access.py` | G | ver matriz |
| `backend/app/public_origin.py` | I | ver matriz |
| `backend/app/push_subscriptions.py` | N | ver matriz |
| `backend/app/seed_admin.py` | A | ver matriz |
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
| `backend/app/unified_checkout.py` | S | ver matriz |
| `backend/app/web_push.py` | N | ver matriz |
| `backend/app/whatsapp_binding.py` | N | ver matriz |
| `backend/app/whatsapp_channel.py` | N | ver matriz |
| `backend/app/whatsapp_delivery.py` | N | ver matriz |
| `backend/app/whatsapp_webhook.py` | N | ver matriz |
| `backend/app/worker.py` | X | ver matriz |
| `scripts/__init__.py` | T | ver matriz |
| `scripts/assert_homolog_schema_head.py` | T | ver matriz |
| `scripts/check_gemma_runtime.py` | T | ver matriz |
| `scripts/deploy-homolog.sh` | T | ver matriz |
| `scripts/embedding_engine_benchmark.py` | T | ver matriz |
| `scripts/face_benchmark.py` | T | ver matriz |
| `scripts/face_spike/__init__.py` | T | ver matriz |
| `scripts/face_spike/arm_smoke.py` | T | ver matriz |
| `scripts/face_spike/dataset.py` | T | ver matriz |
| `scripts/face_spike/harness.py` | T | ver matriz |
| `scripts/face_spike/models.py` | T | ver matriz |
| `scripts/maintain-homolog-data.sh` | T | ver matriz |
| `scripts/operate-facial-rollout-homolog.sh` | T | ver matriz |
| `scripts/preserve_branding.py` | T | ver matriz |
| `scripts/preview_adjustment_smoke.py` | T | ver matriz |
| `scripts/resume-homolog.sh` | T | ver matriz |
| `frontend/app/(public)/admin/account-action.tsx` | U | ver matriz |
| `frontend/app/(public)/admin/reset-password/page.tsx` | U | ver matriz |
| `frontend/app/(public)/admin/verify-email/page.tsx` | U | ver matriz |
| `frontend/app/admin/admin-navigation.tsx` | U | ver matriz |
| `frontend/app/admin/capacity-diagnostics.tsx` | U | ver matriz |
| `frontend/app/admin/capacity-report.ts` | U | ver matriz |
| `frontend/app/admin/clients/client-controls.tsx` | U | ver matriz |
| `frontend/app/admin/clients/client-directory.tsx` | U | ver matriz |
| `frontend/app/admin/clients/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/[galleryId]/orders/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/[galleryId]/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/[galleryId]/pricing/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/admin-photo-preview-dialog.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/client-gallery-card.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/facial-policy-panel.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/folder-processing-panel.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/new/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/pricing-rules.ts` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/[step]/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/page.tsx` | U | ver matriz |
| `frontend/app/admin/galleries/sources/[sourceId]/preview/page.tsx` | U | ver matriz |
| `frontend/app/admin/installation-diagnostics.tsx` | U | ver matriz |
| `frontend/app/admin/layout.tsx` | U | ver matriz |
| `frontend/app/admin/notifications/page.tsx` | U | ver matriz |
| `frontend/app/admin/operations/page.tsx` | U | ver matriz |
| `frontend/app/admin/page.tsx` | U | ver matriz |
| `frontend/app/admin/payments/order-delivery.tsx` | U | ver matriz |
| `frontend/app/admin/payments/page.tsx` | U | ver matriz |
| `frontend/app/admin/payments/payment-actions.tsx` | U | ver matriz |
| `frontend/app/admin/payments/removed-history.tsx` | U | ver matriz |
| `frontend/app/admin/previews/page.tsx` | U | ver matriz |
| `frontend/app/admin/pricing/page.tsx` | U | ver matriz |
| `frontend/app/admin/purchases/page.tsx` | U | ver matriz |
| `frontend/app/admin/settings/facial-engine-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/infinitepay-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/page.tsx` | U | ver matriz |
| `frontend/app/admin/settings/pix-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/security-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/whatsapp-panel.tsx` | U | ver matriz |
| `frontend/app/admin/statistics/page.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/monitor-hint.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/monitor-link.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/page.tsx` | U | ver matriz |
| `frontend/app/admin/system-monitor/request.ts` | U | ver matriz |
| `frontend/app/admin/system-monitor/types.ts` | U | ver matriz |
| `frontend/app/admin/system-monitor/use-permissions.ts` | U | ver matriz |
| `frontend/app/admin/system-monitor/user-tree.tsx` | U | ver matriz |
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
| `frontend/app/library/cart/page.tsx` | U | ver matriz |
| `frontend/app/library/layout.tsx` | U | ver matriz |
| `frontend/app/library/loading.tsx` | U | ver matriz |
| `frontend/app/library/page.tsx` | U | ver matriz |
| `frontend/app/library/purchase-card.tsx` | U | ver matriz |
| `frontend/app/library/purchases/page.tsx` | U | ver matriz |
| `frontend/app/manifest.ts` | U | ver matriz |
| `frontend/app/monitor-activity.tsx` | U | ver matriz |
| `frontend/app/order-album-url.ts` | U | ver matriz |
| `frontend/app/page.tsx` | U | ver matriz |
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
| `frontend/app/validation-ui.tsx` | U | ver matriz |
| `frontend/public/markina-sw.js` | U | ver matriz |

## Rotas HTTP

| Rota | Escopo/critério | Fonte/handler | Dependências atuais | Evidência por critério |
| --- | --- | --- | --- | --- |
| `GET /admin/photo-folders/{folder_id}/processing` | R/P | `backend/app/folder_processing_api.py:47` / `configuration` | sem Depends na assinatura | ver matriz |
| `PATCH /admin/photo-folders/{folder_id}/processing` | R/P | `backend/app/folder_processing_api.py:96` / `save` | sem Depends na assinatura | ver matriz |
| `POST /admin/photo-folders/{folder_id}/processing/preview/enqueue` | R/P | `backend/app/folder_processing_api.py:113` / `enqueue_folder_preview` | sem Depends na assinatura | ver matriz |
| `POST /admin/photo-folders/{folder_id}/processing/facial/reprocess` | R/F | `backend/app/folder_processing_api.py:133` / `reprocess_folder_facial` | sem Depends na assinatura | ver matriz |
| `GET /health` | I/I | `backend/app/main.py:1248` / `health` | sem Depends na assinatura | ver matriz |
| `POST /internal/whatsapp/webhook` | R/N | `backend/app/main.py:1253` / `whatsapp_webhook` | db_session | ver matriz |
| `GET /admin/whatsapp/channel` | R/N | `backend/app/main.py:1290` / `admin_whatsapp_channel` | db_session | ver matriz |
| `PATCH /admin/whatsapp/channel` | R/N | `backend/app/main.py:1305` / `update_admin_whatsapp_channel` | db_session | ver matriz |
| `POST /admin/whatsapp/channel/refresh` | R/N | `backend/app/main.py:1319` / `refresh_admin_whatsapp_channel` | db_session | ver matriz |
| `POST /admin/whatsapp/channel/pairing` | R/N | `backend/app/main.py:1329` / `pair_admin_whatsapp_channel` | db_session | ver matriz |
| `GET /admin/whatsapp/deliveries` | R/N | `backend/app/main.py:1352` / `admin_whatsapp_deliveries` | db_session | ver matriz |
| `POST /admin/whatsapp/deliveries/{delivery_id}/retry` | R/N | `backend/app/main.py:1378` / `retry_admin_whatsapp_delivery` | db_session | ver matriz |
| `POST /auth/client/challenge` | M/A | `backend/app/main.py:1541` / `client_challenge` | db_session | ver matriz |
| `POST /auth/client/resend` | M/A | `backend/app/main.py:1607` / `client_resend` | db_session | ver matriz |
| `POST /auth/client/verify` | M/A | `backend/app/main.py:1632` / `client_verify` | db_session | ver matriz |
| `POST /auth/admin/password` | M/A | `backend/app/main.py:1904` / `admin_password` | db_session | ver matriz |
| `POST /auth/admin/totp` | M/A | `backend/app/main.py:1933` / `admin_totp` | db_session | ver matriz |
| `POST /auth/admin/recovery/challenge` | M/A | `backend/app/main.py:1971` / `admin_recovery_challenge` | db_session | ver matriz |
| `POST /auth/admin/recovery/resend` | M/A | `backend/app/main.py:2012` / `admin_recovery_resend` | db_session | ver matriz |
| `POST /auth/admin/recovery/verify` | M/A | `backend/app/main.py:2035` / `admin_recovery_verify` | db_session | ver matriz |
| `POST /auth/admin/recovery/reset` | M/A | `backend/app/main.py:2060` / `admin_recovery_reset` | db_session | ver matriz |
| `POST /auth/admin/email/confirm` | M/A | `backend/app/main.py:2094` / `confirm_admin_email` | db_session | ver matriz |
| `GET /auth/destination` | M/A | `backend/app/main.py:2142` / `destination` | sem Depends na assinatura | ver matriz |
| `GET /auth/identity` | M/A | `backend/app/main.py:2152` / `authenticated_identity` | db_session | ver matriz |
| `POST /auth/logout` | M/A | `backend/app/main.py:2183` / `logout` | sem Depends na assinatura | ver matriz |
| `POST /auth/revoke-all` | M/A | `backend/app/main.py:2203` / `revoke_all` | sem Depends na assinatura | ver matriz |
| `GET /admin` | M/A | `backend/app/main.py:2214` / `admin_area` | sem Depends na assinatura | ver matriz |
| `GET /admin/email/channel` | M/A | `backend/app/main.py:2220` / `admin_email_channel` | db_session | ver matriz |
| `GET /admin/security/summary` | M/A | `backend/app/main.py:2241` / `admin_security_summary` | db_session | ver matriz |
| `GET /admin/settings/pix` | R/K | `backend/app/main.py:2258` / `admin_global_pix` | db_session | ver matriz |
| `POST /admin/settings/pix/challenge` | R/K | `backend/app/main.py:2265` / `admin_global_pix_challenge` | db_session | ver matriz |
| `POST /admin/settings/pix/confirm` | R/K | `backend/app/main.py:2311` / `admin_global_pix_confirm` | db_session | ver matriz |
| `GET /admin/settings/infinitepay` | R/K | `backend/app/main.py:2344` / `admin_infinitepay` | db_session | ver matriz |
| `POST /admin/settings/infinitepay/challenge` | R/K | `backend/app/main.py:2352` / `admin_infinitepay_challenge` | db_session | ver matriz |
| `POST /admin/settings/infinitepay/confirm` | R/K | `backend/app/main.py:2409` / `admin_infinitepay_confirm` | db_session | ver matriz |
| `POST /admin/settings/infinitepay/resend` | R/K | `backend/app/main.py:2440` / `admin_infinitepay_resend` | db_session | ver matriz |
| `POST /admin/security/password/challenge` | M/A | `backend/app/main.py:2463` / `admin_password_change_challenge` | db_session | ver matriz |
| `POST /admin/security/password/confirm` | M/A | `backend/app/main.py:2496` / `admin_password_change_confirm` | db_session | ver matriz |
| `POST /admin/security/email/challenge` | M/A | `backend/app/main.py:2529` / `admin_email_change_challenge` | db_session | ver matriz |
| `POST /admin/security/email/verify-otp` | M/A | `backend/app/main.py:2568` / `admin_email_change_verify_otp` | db_session | ver matriz |
| `GET /branding` | M/K | `backend/app/main.py:2626` / `public_branding` | db_session | ver matriz |
| `GET /admin/branding` | M/K | `backend/app/main.py:2638` / `admin_branding` | db_session | ver matriz |
| `PATCH /admin/branding` | M/K | `backend/app/main.py:2648` / `update_admin_branding` | db_session | ver matriz |
| `PATCH /admin/branding/protection` | M/K | `backend/app/main.py:2662` / `update_visual_protection` | db_session | ver matriz |
| `PUT /admin/branding/{asset}` | M/K | `backend/app/main.py:2689` / `upload_branding_asset` | db_session | ver matriz |
| `GET /branding/{asset}` | M/K | `backend/app/main.py:2718` / `public_branding_asset` | db_session | ver matriz |
| `GET /admin/validation-summary` | R/L | `backend/app/main.py:2783` / `admin_validation_summary` | db_session | ver matriz |
| `GET /admin/installation-capabilities` | I/O | `backend/app/main.py:2844` / `admin_installation_capabilities` | sem Depends na assinatura | ver matriz |
| `GET /admin/capacity-observability` | I/O | `backend/app/main.py:2855` / `admin_capacity_observability` | sem Depends na assinatura | ver matriz |
| `GET /admin/facial-observability` | I/O | `backend/app/main.py:2868` / `admin_facial_observability` | db_session | ver matriz |
| `GET /admin/facial-engine-experiment` | I/O | `backend/app/main.py:2935` / `admin_facial_engine_experiment` | db_session | ver matriz |
| `PATCH /admin/facial-engine-experiment` | I/O | `backend/app/main.py:2945` / `update_admin_facial_engine_experiment` | db_session | ver matriz |
| `GET /admin/clients` | R/C | `backend/app/main.py:2991` / `admin_clients` | db_session | ver matriz |
| `POST /admin/clients` | R/C | `backend/app/main.py:3006` / `create_client` | db_session | ver matriz |
| `PATCH /admin/clients/{client_id}` | R/C | `backend/app/main.py:3037` / `update_client_name` | db_session | ver matriz |
| `GET /admin/clients/{client_id}/deletion-inventory` | R/L | `backend/app/main.py:3054` / `get_client_deletion_inventory` | db_session | ver matriz |
| `DELETE /admin/clients/{client_id}` | R/L | `backend/app/main.py:3066` / `delete_client` | db_session | ver matriz |
| `GET /admin/parent-galleries` | R/G | `backend/app/main.py:3191` / `admin_parent_galleries` | db_session | ver matriz |
| `GET /admin/parent-galleries/overview` | R/G | `backend/app/main.py:3210` / `parent_gallery_overview` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/editor` | R/G | `backend/app/main.py:3412` / `parent_gallery_editor` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/settings` | R/G | `backend/app/main.py:3521` / `parent_gallery_settings` | db_session | ver matriz |
| `PATCH /admin/parent-galleries/{parent_gallery_id}/settings` | R/G | `backend/app/main.py:3548` / `update_parent_gallery_settings` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/summary` | R/G | `backend/app/main.py:3570` / `parent_gallery_summary` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/cover` | R/G | `backend/app/main.py:3628` / `set_parent_gallery_cover` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/cover` | R/G | `backend/app/main.py:3665` / `clear_parent_gallery_cover` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/sales` | R/S | `backend/app/main.py:3678` / `parent_gallery_sales` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/sales` | R/S | `backend/app/main.py:3703` / `update_parent_gallery_sales` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/details` | R/G | `backend/app/main.py:3730` / `parent_gallery_details` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/cover-photos` | R/G | `backend/app/main.py:3785` / `register_parent_gallery_cover_photo` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-policy` | R/F | `backend/app/main.py:3830` / `admin_parent_gallery_facial_policy` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/facial-policy` | R/F | `backend/app/main.py:3848` / `prepare_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/activate` | R/F | `backend/app/main.py:3880` / `activate_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/suspend` | R/F | `backend/app/main.py:3919` / `suspend_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/revoke` | R/F | `backend/app/main.py:3944` / `revoke_parent_gallery_facial_policy` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-cleanup-proof` | R/F | `backend/app/main.py:3969` / `admin_parent_gallery_facial_cleanup_proof` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-index` | R/F | `backend/app/main.py:3981` / `admin_parent_gallery_facial_index` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/facial-index` | R/F | `backend/app/main.py:4054` / `admin_private_gallery_facial_index` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-index/retry` | R/F | `backend/app/main.py:4125` / `retry_parent_gallery_facial_index` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-index/reprocess` | R/F | `backend/app/main.py:4165` / `reprocess_parent_gallery_facial_index` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:4220` / `admin_parent_gallery_photos` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/available-photos` | R/G | `backend/app/main.py:4243` / `admin_parent_gallery_available_photos` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/folders` | R/G | `backend/app/main.py:4313` / `admin_parent_gallery_folders` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/folders` | R/G | `backend/app/main.py:4398` / `create_photo_folder` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders` | R/G | `backend/app/main.py:4446` / `admin_client_restricted_folders` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders` | R/G | `backend/app/main.py:4499` / `create_admin_client_restricted_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}` | R/G | `backend/app/main.py:4555` / `grant_restricted_folder_client` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}` | R/L | `backend/app/main.py:4620` / `revoke_restricted_folder_client` | db_session | ver matriz |
| `PATCH /admin/photo-folders/{folder_id}` | R/G | `backend/app/main.py:4661` / `rename_photo_folder` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}` | R/L | `backend/app/main.py:4688` / `delete_photo_folder` | db_session | ver matriz |
| `GET /admin/photo-folders/{folder_id}/photos` | R/G | `backend/app/main.py:4723` / `admin_photo_folder_photos` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}/photos/{photo_id}` | R/L | `backend/app/main.py:4770` / `delete_folder_photo_asset` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}/photos` | R/L | `backend/app/main.py:4862` / `delete_folder_photo_assets` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/photos` | R/G | `backend/app/main.py:4895` / `register_folder_photo_asset` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/publish` | R/G | `backend/app/main.py:5023` / `publish_photo_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/publish-ready` | R/G | `backend/app/main.py:5047` / `publish_parent_gallery_ready_photos` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/release` | R/G | `backend/app/main.py:5079` / `release_photo_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries` | R/G | `backend/app/main.py:5111` / `create_parent_gallery` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:5160` / `parent_gallery_public_link_status` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:5189` / `issue_parent_gallery_public_link` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/public-link/rotate` | R/G | `backend/app/main.py:5219` / `rotate_parent_gallery_public_link` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:5253` / `revoke_parent_gallery_public_link` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite` | R/G | `backend/app/main.py:5304` / `issue_parent_gallery_client_invite` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite/rotate` | R/G | `backend/app/main.py:5331` / `rotate_parent_gallery_client_invite` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite` | R/L | `backend/app/main.py:5366` / `revoke_parent_gallery_client_invite` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/deletion-inventory` | R/L | `backend/app/main.py:5458` / `parent_gallery_deletion_inventory` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/unlink-inventory` | R/L | `backend/app/main.py:5490` / `parent_gallery_client_unlink_inventory` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}` | R/G | `backend/app/main.py:5542` / `delete_parent_gallery` | db_session | ver matriz |
| `GET /admin/gallery-lifecycle-operations/{operation_id}` | R/L | `backend/app/main.py:5599` / `gallery_lifecycle_operation_status` | db_session | ver matriz |
| `POST /admin/gallery-lifecycle-operations/{operation_id}/retry` | R/L | `backend/app/main.py:5611` / `retry_gallery_lifecycle_operation` | db_session | ver matriz |
| `POST /admin/gallery-lifecycle-operations/{operation_id}/cancel` | R/L | `backend/app/main.py:5642` / `cancel_gallery_lifecycle_operation` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/clone` | R/G | `backend/app/main.py:5709` / `clone_derived_gallery` | db_session | ver matriz |
| `POST /admin/clients/{client_id}/phone/challenge` | R/C | `backend/app/main.py:5731` / `challenge_client_phone` | db_session | ver matriz |
| `POST /admin/clients/{client_id}/phone` | R/C | `backend/app/main.py:5752` / `change_client_phone` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients` | R/G | `backend/app/main.py:5784` / `parent_gallery_clients` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}` | R/G | `backend/app/main.py:6063` / `link_admin_client_to_parent_gallery` | db_session | ver matriz |
| `PATCH /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/access` | R/G | `backend/app/main.py:6092` / `update_admin_client_gallery_access` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}` | R/L | `backend/app/main.py:6133` / `unlink_admin_client_from_parent_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/selection` | R/S | `backend/app/main.py:6227` / `selection_detail` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/selection/export.{format}` | R/L | `backend/app/main.py:6359` / `export_selection` | db_session | ver matriz |
| `GET /admin/orders/{order_id}/selection/export.{format}` | R/L | `backend/app/main.py:6455` / `export_finalized_order` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/selection/export.{format}` | R/L | `backend/app/main.py:6477` / `export_canonical_selection` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:6570` / `register_photo_asset` | db_session | ver matriz |
| `PUT /admin/photo-assets/{photo_id}/source` | R/G | `backend/app/main.py:6586` / `import_photo_source` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/media-status` | R/G | `backend/app/main.py:6692` / `photo_media_status` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/facial-analysis` | R/F | `backend/app/main.py:6707` / `admin_photo_facial_analysis` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/preview` | R/G | `backend/app/main.py:6731` / `admin_photo_preview` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/watermarked-preview` | R/G | `backend/app/main.py:6759` / `admin_watermarked_photo_preview` | db_session | ver matriz |
| `GET /admin/purchases` | R/S | `backend/app/main.py:6789` / `admin_purchase_history` | db_session | ver matriz |
| `GET /admin/pricing-presets` | R/K | `backend/app/main.py:6928` / `list_progressive_pricing_presets` | db_session | ver matriz |
| `POST /admin/pricing-presets` | R/K | `backend/app/main.py:6944` / `create_progressive_pricing_preset` | db_session | ver matriz |
| `PUT /admin/pricing-presets/{preset_id}` | R/K | `backend/app/main.py:6981` / `update_progressive_pricing_preset` | db_session | ver matriz |
| `DELETE /admin/pricing-presets/{preset_id}` | R/K | `backend/app/main.py:7008` / `deactivate_progressive_pricing_preset` | db_session | ver matriz |
| `POST /admin/pricing-presets/{preset_id}/activate` | R/K | `backend/app/main.py:7024` / `activate_progressive_pricing_preset` | db_session | ver matriz |
| `GET /admin/pricing-presets/{preset_id}/quote` | R/K | `backend/app/main.py:7041` / `simulate_progressive_pricing_preset` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/pricing` | R/K | `backend/app/main.py:7255` / `admin_parent_gallery_pricing` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/pricing` | R/K | `backend/app/main.py:7265` / `save_admin_parent_gallery_pricing` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/pricing` | R/K | `backend/app/main.py:7284` / `admin_gallery_pricing` | db_session | ver matriz |
| `PUT /admin/derived-galleries/{gallery_id}/pricing` | R/K | `backend/app/main.py:7303` / `save_admin_gallery_pricing` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/orders` | R/S | `backend/app/main.py:7320` / `admin_gallery_orders` | db_session | ver matriz |
| `POST /admin/derived-galleries` | R/G | `backend/app/main.py:7387` / `create_derived_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:7431` / `private_gallery_link_status` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:7475` / `issue_private_gallery_link` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/link/rotate` | R/G | `backend/app/main.py:7492` / `rotate_private_gallery_link` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:7512` / `revoke_private_gallery_link` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/invite/rotate` | R/G | `backend/app/main.py:7530` / `rotate_private_gallery_invite` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/invite` | R/G | `backend/app/main.py:7546` / `revoke_private_gallery_invite` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/members` | R/G | `backend/app/main.py:7608` / `private_gallery_members` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members` | R/G | `backend/app/main.py:7675` / `add_private_gallery_member` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members/{client_id}/block` | R/G | `backend/app/main.py:7839` / `block_private_gallery_member` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members/{client_id}/unblock` | R/G | `backend/app/main.py:7858` / `unblock_private_gallery_member` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/members/{client_id}` | R/G | `backend/app/main.py:7877` / `unlink_private_gallery_member` | db_session | ver matriz |
| `GET /admin/notifications` | R/N | `backend/app/main.py:7896` / `admin_gallery_membership_notifications` | db_session | ver matriz |
| `POST /admin/notifications/{notification_id}/read` | R/N | `backend/app/main.py:7956` / `read_admin_gallery_membership_notification` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/upload-batches` | R/G | `backend/app/main.py:7970` / `list_private_upload_batches` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/upload-batches` | R/G | `backend/app/main.py:7983` / `begin_private_upload_batch` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/upload-batches/{batch_id}/close` | R/G | `backend/app/main.py:7998` / `finish_private_upload_batch` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/folders` | R/G | `backend/app/main.py:8014` / `admin_private_gallery_folders` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/folders` | R/G | `backend/app/main.py:8056` / `create_private_gallery_folder` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/photos` | R/G | `backend/app/main.py:8087` / `admin_private_gallery_photos` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/photos` | R/G | `backend/app/main.py:8286` / `add_admin_private_gallery_photos` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/photos/{photo_id}` | R/L | `backend/app/main.py:8306` / `remove_admin_private_gallery_photo` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:8373` / `delete_derived_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries` | R/G | `backend/app/main.py:8425` / `list_derived_galleries` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:8480` / `derived_gallery_detail` | db_session | ver matriz |
| `PATCH /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:8551` / `update_derived_gallery` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/renew` | R/G | `backend/app/main.py:8568` / `renew_gallery_selection` | db_session | ver matriz |
| `GET /admin/gallery-reopening-requests` | R/S | `backend/app/main.py:8614` / `list_gallery_reopening_requests` | db_session | ver matriz |
| `POST /admin/gallery-reopening-requests/{request_id}/decision` | R/S | `backend/app/main.py:8662` / `decide_gallery_reopening_request` | db_session | ver matriz |
| `POST /admin/gallery-reopening-notifications/{notification_id}/retry` | R/N | `backend/app/main.py:8704` / `retry_gallery_reopening_notification` | db_session | ver matriz |
| `GET /admin/statistics` | R/L | `backend/app/main.py:8727` / `admin_statistics` | db_session | ver matriz |
| `GET /admin/statistics/filters` | R/L | `backend/app/main.py:8773` / `admin_statistics_filters` | db_session | ver matriz |
| `GET /admin/statistics/selected-not-purchased.txt` | R/L | `backend/app/main.py:8802` / `export_selected_not_purchased_txt` | db_session | ver matriz |
| `GET /admin/statistics/purchased.txt` | R/L | `backend/app/main.py:8828` / `export_purchased_txt` | db_session | ver matriz |
| `GET /library` | R/G | `backend/app/main.py:8854` / `client_library` | db_session | ver matriz |
| `GET /library/cart` | R/S | `backend/app/main.py:9191` / `unified_cart` | db_session | ver matriz |
| `POST /library/cart/prepare` | R/S | `backend/app/main.py:9196` / `prepare_unified_cart` | db_session | ver matriz |
| `POST /library/cart/prepare-card` | R/S | `backend/app/main.py:9215` / `prepare_unified_card` | db_session | ver matriz |
| `GET /infinitepay/return` | R/S | `backend/app/main.py:9248` / `infinitepay_return` | db_session | ver matriz |
| `POST /library/cart/{gallery_id}/finalize` | R/S | `backend/app/main.py:9307` / `finalize_unified_selection` | db_session | ver matriz |
| `POST /library/payments/{group_id}/report` | R/S | `backend/app/main.py:9320` / `report_unified_payment` | db_session | ver matriz |
| `DELETE /library/cart/{gallery_id}` | R/S | `backend/app/main.py:9334` / `remove_unified_cart_group` | db_session | ver matriz |
| `DELETE /library/cart/{gallery_id}/photos/{photo_id}` | R/S | `backend/app/main.py:9364` / `remove_unified_cart_photo` | db_session | ver matriz |
| `GET /library/purchases` | R/S | `backend/app/main.py:9392` / `client_purchase_history` | db_session | ver matriz |
| `GET /library/purchases/items/{item_id}/preview` | R/S | `backend/app/main.py:9611` / `client_purchased_photo_preview` | db_session | ver matriz |
| `GET /library/history/items/{item_id}/preview` | R/S | `backend/app/main.py:9647` / `client_historical_preview` | db_session | ver matriz |
| `GET /library/history/items/{item_id}/delivery` | R/S | `backend/app/main.py:9659` / `client_historical_delivery` | db_session | ver matriz |
| `GET /gallery/{gallery_id}` | R/G | `backend/app/main.py:9684` / `gallery_area` | sem Depends na assinatura | ver matriz |
| `GET /gallery/{gallery_id}/photos` | R/G | `backend/app/main.py:9714` / `gallery_photos` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/folders` | R/G | `backend/app/main.py:9767` / `gallery_released_folders` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/review` | R/S | `backend/app/main.py:9815` / `gallery_review` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/cover-preview` | R/G | `backend/app/main.py:9943` / `client_gallery_cover_preview` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/photos/{photo_id}/preview` | R/G | `backend/app/main.py:9968` / `client_photo_preview` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:10011` / `select_photo` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:10088` / `select_photo_from_public_gallery` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:10145` / `unselect_photo_from_public_gallery` | db_session | ver matriz |
| `POST /public-gallery/access` | R/G | `backend/app/main.py:10227` / `access_public_gallery_with_session` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}` | R/G | `backend/app/main.py:10267` / `public_gallery_for_client` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-search` | R/F | `backend/app/main.py:10324` / `public_gallery_facial_search_availability` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos/{photo_id}/face-regions` | R/F | `backend/app/main.py:10363` / `public_photo_face_regions` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/face-region-searches` | R/F | `backend/app/main.py:10389` / `public_face_region_search` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/facial-searches` | R/F | `backend/app/main.py:10419` / `create_public_gallery_facial_search` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-searches/latest` | R/F | `backend/app/main.py:10491` / `latest_public_gallery_facial_search_result` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}` | R/F | `backend/app/main.py:10511` / `public_gallery_facial_search_result` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}` | R/F | `backend/app/main.py:10533` / `cancel_public_gallery_facial_search` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}/candidates/{photo_id}` | R/F | `backend/app/main.py:10563` / `reject_public_gallery_facial_candidate` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}/candidates/{photo_id}/selection` | R/F | `backend/app/main.py:10592` / `select_public_gallery_facial_candidate` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:10641` / `public_gallery_photos` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/cover-preview` | R/G | `backend/app/main.py:10755` / `public_gallery_cover_preview` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos/{photo_id}/preview` | R/G | `backend/app/main.py:10783` / `public_gallery_photo_preview` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:10839` / `favorite_canonical_photo` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:10871` / `unfavorite_canonical_photo` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/view` | R/S | `backend/app/main.py:10893` / `record_canonical_photo_view` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/comments` | R/S | `backend/app/main.py:10924` / `create_canonical_photo_comment` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/comments` | R/S | `backend/app/main.py:10950` / `canonical_client_comments` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:10981` / `remove_canonical_comment` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:11008` / `unselect_photo` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/cart` | R/S | `backend/app/main.py:11074` / `client_cart` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/reopening-requests` | R/S | `backend/app/main.py:11087` / `client_gallery_reopening_request` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/reopening-requests` | R/S | `backend/app/main.py:11110` / `request_gallery_reopening` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/reopening-requests` | R/S | `backend/app/main.py:11176` / `canonical_gallery_reopening_request` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/reopening-requests` | R/S | `backend/app/main.py:11198` / `request_canonical_gallery_reopening` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/checkout` | R/S | `backend/app/main.py:11259` / `checkout_gallery` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/orders/{order_id}/payment-communications` | R/S | `backend/app/main.py:11288` / `communicate_payment` | db_session | ver matriz |
| `POST /admin/payment-communications/{communication_id}/decision` | R/S | `backend/app/main.py:11387` / `decide_payment_communication` | db_session | ver matriz |
| `POST /admin/payment-communications/{communication_id}/correction` | R/S | `backend/app/main.py:11436` / `correct_payment_confirmation` | db_session | ver matriz |
| `PUT /admin/orders/{order_id}/delivery` | R/S | `backend/app/main.py:11554` / `update_order_delivery` | db_session | ver matriz |
| `POST /admin/orders/{order_id}/delivery/resend` | R/S | `backend/app/main.py:11570` / `resend_order_delivery` | db_session | ver matriz |
| `GET /push/subscription` | R/N | `backend/app/main.py:11592` / `push_subscription_state` | db_session | ver matriz |
| `POST /push/subscription` | R/N | `backend/app/main.py:11613` / `register_push_subscription` | db_session | ver matriz |
| `DELETE /push/subscription` | R/N | `backend/app/main.py:11640` / `unregister_push_subscription` | db_session | ver matriz |
| `GET /admin/notification-settings` | R/K | `backend/app/main.py:11668` / `list_notification_settings` | db_session | ver matriz |
| `PUT /admin/notification-settings/{event_type}` | R/K | `backend/app/main.py:11676` / `update_notification_setting` | db_session | ver matriz |
| `PUT /admin/payment-message-templates/{kind}` | R/K | `backend/app/main.py:11690` / `save_payment_template` | db_session | ver matriz |
| `GET /admin/payment-message-templates` | R/K | `backend/app/main.py:11707` / `list_payment_templates` | db_session | ver matriz |
| `GET /admin/removed-photo-movements` | R/L | `backend/app/main.py:11722` / `admin_removed_photo_movements` | db_session | ver matriz |
| `GET /admin/payment-communications` | R/S | `backend/app/main.py:11741` / `list_payment_communications` | db_session | ver matriz |
| `POST /admin/payment-notifications/{notification_id}/retry` | R/N | `backend/app/main.py:12332` / `retry_payment_notification` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/payment-communications` | R/S | `backend/app/main.py:12354` / `client_payment_communications` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/orders/{order_id}` | R/S | `backend/app/main.py:12374` / `client_pending_order` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:12448` / `favorite_photo` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:12482` / `unfavorite_photo` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/comments` | R/S | `backend/app/main.py:12503` / `create_photo_comment` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/comments` | R/S | `backend/app/main.py:12534` / `client_comments` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:12558` / `remove_own_comment` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/comments` | R/S | `backend/app/main.py:12581` / `admin_comments` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:12609` / `remove_comment_as_admin` | db_session | ver matriz |
| `GET /admin/preview-adjustment/galleries/{gallery_id}/configuration` | R/P | `backend/app/preview_adjustment/api.py:34` / `configuration` | sem Depends na assinatura | ver matriz |
| `PATCH /admin/preview-adjustment/galleries/{gallery_id}/configuration` | R/P | `backend/app/preview_adjustment/api.py:49` / `save_configuration` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/galleries` | R/P | `backend/app/preview_adjustment/api.py:65` / `galleries` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/galleries/{gallery_id}` | R/P | `backend/app/preview_adjustment/api.py:84` / `gallery_progress` | sem Depends na assinatura | ver matriz |
| `POST /admin/preview-adjustment/galleries/{gallery_id}/enqueue` | R/P | `backend/app/preview_adjustment/api.py:127` / `enqueue_gallery` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/photos/{photo_id}/{version}` | R/P | `backend/app/preview_adjustment/api.py:165` / `compare` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/capabilities` | I/O | `backend/app/system_monitor/routes.py:48` / `capabilities` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor` | I/O | `backend/app/system_monitor/routes.py:56` / `summary` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/tree` | I/O | `backend/app/system_monitor/routes.py:63` / `tree` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/incidents` | I/O | `backend/app/system_monitor/routes.py:79` / `incidents` | sem Depends na assinatura | ver matriz |
| `GET /admin/system-monitor/report` | I/O | `backend/app/system_monitor/routes.py:87` / `report` | sem Depends na assinatura | ver matriz |
| `GET /auth/activity-policy` | M/A | `backend/app/system_monitor/routes.py:108` / `activity_policy` | sem Depends na assinatura | ver matriz |
| `POST /auth/activity` | M/A | `backend/app/system_monitor/routes.py:117` / `activity` | sem Depends na assinatura | ver matriz |

## Produtores queries gates e efeitos

| Fonte/função | Critério/teste | Sinal | Chamada | Evidência por critério |
| --- | --- | --- | --- | --- |
| `backend/app/acervo_context.py:14` / `require_active_owner` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/acervo_context.py:24` / `owned_record` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/acervo_context.py:25` / `owned_record` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/acervo_context.py:32` / `client_tenant_id` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/acervo_context.py:35` / `client_tenant_id` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/acervo_context.py:25` / `owned_record` | G | query/ORM | `select` | ver matriz |
| `backend/app/admin_account.py:94` / `_queue_admin_otp` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/admin_account.py:96` / `_queue_admin_otp` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/admin_account.py:97` / `_queue_admin_otp` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/admin_account.py:101` / `_queue_admin_otp` | A | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/admin_account.py:122` / `_queue_admin_otp` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/admin_account.py:163` / `create_security_challenge` | A | produtor | `AdminSecurityChallenge` | ver matriz |
| `backend/app/admin_account.py:178` / `create_security_challenge` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/admin_account.py:196` / `verify_security_challenge` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:228` / `resend_security_challenge` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:275` / `issue_password_reset_email` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:282` / `issue_password_reset_email` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:303` / `challenge_target` | A | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:307` / `challenge_target` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/admin_account.py:316` / `token_target` | A | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:320` / `token_target` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/admin_account.py:342` / `issue_email_verification` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/admin_account.py:351` / `issue_email_verification` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:369` / `queue_previous_email_notice` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:394` / `active_admin_for_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:113` / `_queue_admin_otp` | A | efeito potencial | `encrypt_otp` | ver matriz |
| `backend/app/admin_account.py:137` / `create_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:138` / `create_security_challenge` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/admin_account.py:152` / `create_security_challenge` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_account.py:175` / `create_security_challenge` | A | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:200` / `verify_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:232` / `resend_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:389` / `active_admin_for_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/admin_account.py:97` / `_queue_admin_otp` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_account.py:114` / `_queue_admin_otp` | A | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/admin_account.py:342` / `issue_email_verification` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_account.py:52` / `require_security_owner` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/admin_account.py:141` / `create_security_challenge` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/admin_account.py:153` / `create_security_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:59` / `encrypt_sensitive_payload` | A | efeito potencial | `AESGCM(sensitive_payload_key()).encrypt` | ver matriz |
| `backend/app/admin_security.py:86` / `issue_admin_action_token` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:96` / `issue_admin_action_token` | A | produtor | `AdminActionToken` | ver matriz |
| `backend/app/admin_security.py:108` / `issue_admin_action_token` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/admin_security.py:119` / `consume_admin_action_token` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/admin_security.py:128` / `consume_admin_action_token` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/admin_security.py:143` / `invalidate_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:151` / `invalidate_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:171` / `cleanup_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:66` / `decrypt_sensitive_payload` | A | efeito potencial | `AESGCM(sensitive_payload_key()).decrypt` | ver matriz |
| `backend/app/admin_security.py:105` / `issue_admin_action_token` | A | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_security.py:165` / `cleanup_admin_security_material` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/admin_security.py:176` / `cleanup_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:180` / `cleanup_admin_security_material` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_security.py:168` / `cleanup_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:176` / `cleanup_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:180` / `cleanup_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:193` / `cleanup_admin_security_material` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/admin_security.py:87` / `issue_admin_action_token` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:120` / `consume_admin_action_token` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:144` / `invalidate_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:152` / `invalidate_admin_security_material` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_security.py:129` / `consume_admin_action_token` | A | query/ORM | `update` | ver matriz |
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
| `backend/app/auth.py:3190` / `audit` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3232` / `create_challenge` | A | produtor | `AuthChallenge` | ver matriz |
| `backend/app/auth.py:3244` / `create_challenge` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3260` / `enqueue_client_otp_delivery` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:3262` / `enqueue_client_otp_delivery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3268` / `enqueue_client_otp_delivery` | A | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/auth.py:3295` / `enqueue_client_otp_delivery` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3332` / `resend_client_challenge` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:3333` / `resend_client_challenge` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3353` / `resend_client_challenge` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3382` / `consume_challenge` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3426` / `minimize_client_challenge_pii` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3446` / `cleanup_expired_client_otp_pii` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/auth.py:3493` / `create_session` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3504` / `create_session` | A | produtor | `AuthSession` | ver matriz |
| `backend/app/auth.py:3513` / `create_session` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3533` / `current_session` | A | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/auth.py:3569` / `revoke_subject_sessions` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3576` / `revoke_subject_sessions` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:64` / `expired` | A | efeito potencial | `value.replace` | ver matriz |
| `backend/app/auth.py:84` / `_enable_sqlite_foreign_keys` | A | query/ORM | `cursor.execute` | ver matriz |
| `backend/app/auth.py:3190` / `audit` | A | produtor | `AuditEvent` | ver matriz |
| `backend/app/auth.py:3198` / `enforce_rate_limit` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3230` / `create_challenge` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:3280` / `enqueue_client_otp_delivery` | A | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/auth.py:3281` / `enqueue_client_otp_delivery` | A | efeito potencial | `encrypt_otp` | ver matriz |
| `backend/app/auth.py:3304` / `require_client_channel` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/auth.py:3310` / `require_client_auth_tenant` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:3371` / `resend_client_challenge` | A | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/auth.py:3451` / `cleanup_expired_client_otp_pii` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3461` / `cleanup_expired_client_otp_pii` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/auth.py:3537` / `current_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:1451` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1484` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1495` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:3378` / `consume_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3477` / `create_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/auth.py:3478` / `create_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:336` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:336` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:343` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:344` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:350` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:351` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:587` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:588` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:595` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:596` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:602` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:603` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:840` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:841` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:873` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:874` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:906` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:907` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:963` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:964` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1129` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1133` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1142` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1147` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1359` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1360` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1368` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1369` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1375` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1376` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1457` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1468` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1485` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1500` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1507` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1754` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1755` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1760` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1761` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:3262` / `enqueue_client_otp_delivery` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3354` / `resend_client_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3427` / `minimize_client_challenge_pii` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3494` / `create_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3548` / `current_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/auth.py:3549` / `current_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:3569` / `revoke_subject_sessions` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3577` / `revoke_subject_sessions` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3199` / `enforce_rate_limit` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3452` / `cleanup_expired_client_otp_pii` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3486` / `create_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3537` / `current_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3333` / `resend_client_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3556` / `current_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3486` / `create_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3556` / `current_session` | A | query/ORM | `select` | ver matriz |
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
| `backend/app/canonical_selection.py:49` / `_selection_quantity` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/canonical_selection.py:65` / `select_canonical_photo` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/canonical_selection.py:66` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:77` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:141` / `unselect_canonical_photo` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/canonical_selection.py:148` / `unselect_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:149` / `unselect_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:157` / `unselect_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:53` / `_selection_quantity` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:117` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:163` / `unselect_canonical_photo` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/canonical_selection.py:104` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:82` / `select_canonical_photo` | S | produtor | `GalleryClientState` | ver matriz |
| `backend/app/canonical_selection.py:91` / `select_canonical_photo` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/canonical_selection.py:95` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:120` / `select_canonical_photo` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/canonical_selection.py:73` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:111` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:120` / `select_canonical_photo` | S | produtor | `PhotoSelection` | ver matriz |
| `backend/app/canonical_selection.py:128` / `select_canonical_photo` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/canonical_selection.py:157` / `unselect_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:54` / `_selection_quantity` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:66` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:148` / `unselect_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:149` / `unselect_canonical_photo` | S | query/ORM | `select` | ver matriz |
| `backend/app/canonical_selection.py:105` / `select_canonical_photo` | S | query/ORM | `select` | ver matriz |
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
| `backend/app/checkout.py:41` / `lock_client_commerce` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:44` / `lock_client_commerce` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:45` / `lock_client_commerce` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:55` / `lock_client_commerce` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:65` / `client_photo_is_frozen` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:88` / `client_photo_is_frozen_any` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:107` / `selected_photos` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:156` / `_checkout_material` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:170` / `_checkout_material` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:187` / `_checkout_material` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:219` / `_synchronize_order` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:259` / `_synchronize_order` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/checkout.py:261` / `_synchronize_order` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:289` / `remove_canonical_cart_selection` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:296` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:297` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:316` / `remove_canonical_cart_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:319` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:345` / `create_pending_checkout` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:347` / `create_pending_checkout` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:374` / `create_pending_checkout` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:404` / `synchronize_editable_draft` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:407` / `synchronize_editable_draft` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:421` / `synchronize_editable_draft` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:424` / `synchronize_editable_draft` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:445` / `synchronize_editable_draft` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:466` / `freeze_pending_checkout` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/checkout.py:469` / `freeze_pending_checkout` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:484` / `freeze_pending_checkout` | S | gate | `owned_record` | ver matriz |
| `backend/app/checkout.py:494` / `freeze_pending_checkout` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:67` / `client_photo_is_frozen` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:89` / `client_photo_is_frozen_any` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:122` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:135` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:270` / `_synchronize_order` | S | query/ORM | `folders_by_id.get` | ver matriz |
| `backend/app/checkout.py:271` / `_synchronize_order` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/checkout.py:313` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:328` / `remove_canonical_cart_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:330` / `remove_canonical_cart_selection` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/checkout.py:361` / `create_pending_checkout` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:382` / `create_pending_checkout` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/checkout.py:432` / `synchronize_editable_draft` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:433` / `synchronize_editable_draft` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/checkout.py:111` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:115` / `selected_photos` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:202` / `_checkout_material` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/checkout.py:272` / `_synchronize_order` | S | produtor | `SaleOrderItem` | ver matriz |
| `backend/app/checkout.py:335` / `remove_canonical_cart_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:439` / `synchronize_editable_draft` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/checkout.py:332` / `remove_canonical_cart_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:436` / `synchronize_editable_draft` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/checkout.py:131` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:303` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:261` / `_synchronize_order` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:316` / `remove_canonical_cart_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:348` / `create_pending_checkout` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:425` / `synchronize_editable_draft` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:495` / `freeze_pending_checkout` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:123` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:328` / `remove_canonical_cart_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:432` / `synchronize_editable_draft` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:44` / `lock_client_commerce` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:46` / `lock_client_commerce` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:56` / `lock_client_commerce` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:111` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:171` / `_checkout_material` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:203` / `_checkout_material` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:296` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:297` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:319` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:335` / `remove_canonical_cart_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:408` / `synchronize_editable_draft` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:439` / `synchronize_editable_draft` | S | query/ORM | `delete` | ver matriz |
| `backend/app/checkout.py:470` / `freeze_pending_checkout` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:68` / `client_photo_is_frozen` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:90` / `client_photo_is_frozen_any` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:332` / `remove_canonical_cart_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:436` / `synchronize_editable_draft` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:136` / `selected_photos` | S | query/ORM | `select` | ver matriz |
| `backend/app/checkout.py:362` / `create_pending_checkout` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:29` / `client_carts_by_gallery_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:92` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:150` / `client_carts_by_gallery_payload` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/client_commerce.py:159` / `client_photo_states` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:224` / `client_orders_by_gallery_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:249` / `client_orders_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:336` / `client_orders_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/client_commerce.py:44` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:68` / `client_carts_by_gallery_payload` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_commerce.py:104` / `client_carts_by_gallery_payload` | S | query/ORM | `drafts_by_gallery.get` | ver matriz |
| `backend/app/client_commerce.py:121` / `client_carts_by_gallery_payload` | S | query/ORM | `parents.get` | ver matriz |
| `backend/app/client_commerce.py:136` / `client_carts_by_gallery_payload` | S | query/ORM | `payload.update` | ver matriz |
| `backend/app/client_commerce.py:165` / `client_photo_states` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:180` / `client_photo_states` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_commerce.py:232` / `client_orders_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:259` / `client_orders_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:270` / `client_orders_by_gallery_payload` | S | query/ORM | `communications.get` | ver matriz |
| `backend/app/client_commerce.py:55` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:75` / `client_carts_by_gallery_payload` | S | query/ORM | `draft_items[order_id].add` | ver matriz |
| `backend/app/client_commerce.py:89` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:271` / `client_orders_by_gallery_payload` | S | query/ORM | `deliveries.get` | ver matriz |
| `backend/app/client_commerce.py:81` / `client_carts_by_gallery_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_commerce.py:45` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:69` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:166` / `client_photo_states` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:56` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:89` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:93` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:250` / `client_orders_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:81` / `client_carts_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:233` / `client_orders_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:260` / `client_orders_by_gallery_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/client_commerce.py:181` / `client_photo_states` | S | query/ORM | `select` | ver matriz |
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
| `backend/app/client_lifecycle.py:100` / `list_client_directory` | L | efeito potencial | `select(func.count(func.distinct(DerivedGalleryMembership.derived_gallery_id))).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').correlate(Client).scalar_subquery` | ver matriz |
| `backend/app/client_lifecycle.py:110` / `list_client_directory` | L | efeito potencial | `select(func.count(DerivedGallery.id)).where(DerivedGallery.tenant_id == tenant_id, DerivedGallery.client_id == Client.id, ~select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').exists()).correlate(Client).scalar_subquery` | ver matriz |
| `backend/app/client_lifecycle.py:200` / `deletion_inventory` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/client_lifecycle.py:356` / `delete_client_operational_graph` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/client_lifecycle.py:363` / `delete_client_operational_graph` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:373` / `delete_client_operational_graph` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:574` / `delete_client_operational_graph` | L | query/ORM | `db.delete` | ver matriz |
| `backend/app/client_lifecycle.py:577` / `delete_client_operational_graph` | L | produtor | `ClientDeletionReceipt` | ver matriz |
| `backend/app/client_lifecycle.py:588` / `delete_client_operational_graph` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/client_lifecycle.py:590` / `delete_client_operational_graph` | L | query/ORM | `db.add` | ver matriz |
| `backend/app/client_lifecycle.py:669` / `_client_auth_phones` | L | query/ORM | `phones.add` | ver matriz |
| `backend/app/client_lifecycle.py:689` / `_shared_gallery_successor` | L | gate | `owned_record` | ver matriz |
| `backend/app/client_lifecycle.py:754` / `_delete_where` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_lifecycle.py:85` / `list_client_directory` | L | gate | `require_identity_tenant` | ver matriz |
| `backend/app/client_lifecycle.py:173` / `list_client_directory` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_lifecycle.py:286` / `deletion_inventory` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:293` / `deletion_inventory` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:382` / `delete_client_operational_graph` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:442` / `delete_client_operational_graph` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:449` / `delete_client_operational_graph` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/client_lifecycle.py:491` / `delete_client_operational_graph` | L | gate | `owned_record` | ver matriz |
| `backend/app/client_lifecycle.py:531` / `delete_client_operational_graph` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:591` / `delete_client_operational_graph` | L | produtor | `AuditEvent` | ver matriz |
| `backend/app/client_lifecycle.py:617` / `remove_facial_reference_files` | L | gate | `require_active_owner` | ver matriz |
| `backend/app/client_lifecycle.py:625` / `receipt_payload` | L | efeito potencial | `completed_at.replace` | ver matriz |
| `backend/app/client_lifecycle.py:641` / `_client_gallery_ids` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:662` / `_client_auth_phones` | L | query/ORM | `db.scalars` | ver matriz |
| `backend/app/client_lifecycle.py:693` / `_shared_gallery_successor` | L | efeito potencial | `select(DerivedGalleryMembership.client_id).where(DerivedGalleryMembership.tenant_id == tenant_id).where(DerivedGalleryMembership.derived_gallery_id == gallery_id, DerivedGalleryMembership.client_id != excluded_client_id, DerivedGalleryMembership.status != 'unlinked').order_by` | ver matriz |
| `backend/app/client_lifecycle.py:734` / `_shared_gallery_successor` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:100` / `list_client_directory` | L | efeito potencial | `select(func.count(func.distinct(DerivedGalleryMembership.derived_gallery_id))).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').correlate` | ver matriz |
| `backend/app/client_lifecycle.py:110` / `list_client_directory` | L | efeito potencial | `select(func.count(DerivedGallery.id)).where(DerivedGallery.tenant_id == tenant_id, DerivedGallery.client_id == Client.id, ~select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').exists()).correlate` | ver matriz |
| `backend/app/client_lifecycle.py:145` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:603` / `delete_client_operational_graph` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:742` / `_count` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:303` / `deletion_inventory` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:316` / `deletion_inventory` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/client_lifecycle.py:358` / `delete_client_operational_graph` | L | gate | `require_admin_tenant` | ver matriz |
| `backend/app/client_lifecycle.py:754` / `_delete_where` | L | query/ORM | `delete` | ver matriz |
| `backend/app/client_lifecycle.py:207` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:284` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:388` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:636` / `_client_gallery_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:364` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:466` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:706` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:710` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:714` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:718` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:722` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:726` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:90` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:100` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:110` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:114` / `list_client_directory` | L | efeito potencial | `select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id, DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id, DerivedGalleryMembership.client_id == Client.id, DerivedGalleryMembership.status != 'unlinked').exists` | ver matriz |
| `backend/app/client_lifecycle.py:127` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:133` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:139` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:287` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:294` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:382` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:443` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:532` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:663` / `_client_auth_phones` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:373` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:604` / `delete_client_operational_graph` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:693` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:700` / `_shared_gallery_successor` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:450` / `delete_client_operational_graph` | L | query/ORM | `update` | ver matriz |
| `backend/app/client_lifecycle.py:642` / `_client_gallery_ids` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:742` / `_count` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:114` / `list_client_directory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:304` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
| `backend/app/client_lifecycle.py:317` / `deletion_inventory` | L | query/ORM | `select` | ver matriz |
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
| `backend/app/commercial_projection.py:65` / `build_commercial_projections` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/commercial_projection.py:85` / `build_commercial_projections` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/commercial_projection.py:88` / `build_commercial_projections` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/commercial_projection.py:163` / `build_commercial_projections` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_projection.py:86` / `build_commercial_projections` | S | query/ORM | `available_photo_ids[gallery_id].add` | ver matriz |
| `backend/app/commercial_projection.py:99` / `build_commercial_projections` | S | query/ORM | `selected_photo_ids[gallery_id, client_id].add` | ver matriz |
| `backend/app/commercial_projection.py:101` / `build_commercial_projections` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/commercial_projection.py:181` / `build_commercial_projections` | S | query/ORM | `galleries.get` | ver matriz |
| `backend/app/commercial_projection.py:147` / `build_commercial_projections` | S | query/ORM | `item_ids_by_order[row.id].add` | ver matriz |
| `backend/app/commercial_projection.py:149` / `build_commercial_projections` | S | query/ORM | `pending_review_order_ids.add` | ver matriz |
| `backend/app/commercial_projection.py:151` / `build_commercial_projections` | S | query/ORM | `purchased_photo_ids[row.derived_gallery_id_snapshot, row.client_id].add` | ver matriz |
| `backend/app/commercial_projection.py:182` / `build_commercial_projections` | S | query/ORM | `available_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:185` / `build_commercial_projections` | S | query/ORM | `orders_by_key.get` | ver matriz |
| `backend/app/commercial_projection.py:200` / `build_commercial_projections` | S | query/ORM | `latest_reopening.get` | ver matriz |
| `backend/app/commercial_projection.py:73` / `build_commercial_projections` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/commercial_projection.py:159` / `build_commercial_projections` | S | query/ORM | `selected_photo_ids[row.derived_gallery_id_snapshot, row.client_id].add` | ver matriz |
| `backend/app/commercial_projection.py:80` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:89` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:209` / `build_commercial_projections` | S | query/ORM | `purchased_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:76` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:206` / `build_commercial_projections` | S | query/ORM | `selected_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:207` / `build_commercial_projections` | S | query/ORM | `purchased_photo_ids.get` | ver matriz |
| `backend/app/commercial_projection.py:225` / `build_commercial_projections` | S | query/ORM | `scopes.get` | ver matriz |
| `backend/app/commercial_projection.py:164` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:73` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
| `backend/app/commercial_projection.py:102` / `build_commercial_projections` | S | query/ORM | `select` | ver matriz |
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
| `backend/app/email_delivery.py:182` / `email_provider_from_environment` | N | efeito potencial | `_sender_domain` | ver matriz |
| `backend/app/email_delivery.py:237` / `enqueue_email` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/email_delivery.py:242` / `enqueue_email` | N | produtor | `EmailDelivery` | ver matriz |
| `backend/app/email_delivery.py:251` / `enqueue_email` | N | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/email_delivery.py:255` / `enqueue_email` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/email_delivery.py:89` / `send` | N | efeito potencial | `_sender_domain` | ver matriz |
| `backend/app/email_delivery.py:238` / `enqueue_email` | N | query/ORM | `select` | ver matriz |
| `backend/app/email_delivery.py:107` / `send` | N | efeito potencial | `client.send_message` | ver matriz |
| `backend/app/email_delivery.py:119` / `send` | N | efeito potencial | `client.send_message` | ver matriz |
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
| `backend/app/facial/crypto.py:91` / `encrypt` | F | efeito potencial | `AESGCM(self._keys[self._active_key_id]).encrypt` | ver matriz |
| `backend/app/facial/crypto.py:103` / `decrypt` | F | query/ORM | `self._keys.get` | ver matriz |
| `backend/app/facial/crypto.py:120` / `rotate` | F | efeito potencial | `self.decrypt` | ver matriz |
| `backend/app/facial/crypto.py:123` / `rotate` | F | efeito potencial | `self.encrypt` | ver matriz |
| `backend/app/facial/crypto.py:107` / `decrypt` | F | efeito potencial | `AESGCM(key).decrypt` | ver matriz |
| `backend/app/facial/engine.py:62` / `replace_photo_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:76` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:85` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:95` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:112` / `replace_photo_index` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/engine.py:114` / `replace_photo_index` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/engine.py:130` / `revalidate` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:131` / `revalidate` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:132` / `revalidate` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:162` / `replace_photo_index` | F | efeito potencial | `json.dumps({'embedding': face.embedding, 'quality': assessment.encrypted_indicators()}, separators=(',', ':'), sort_keys=True).encode` | ver matriz |
| `backend/app/facial/engine.py:170` / `replace_photo_index` | F | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/facial/engine.py:211` / `replace_photo_index` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/engine.py:219` / `replace_photo_index` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/engine.py:252` / `search_gallery_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:259` / `search_gallery_index` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/engine.py:288` / `search_gallery_index` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/engine.py:291` / `search_gallery_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:292` / `search_gallery_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:310` / `search_gallery_index` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/engine.py:343` / `search_gallery_index` | F | query/ORM | `best_by_photo.get` | ver matriz |
| `backend/app/facial/engine.py:188` / `replace_photo_index` | F | produtor | `PhotoFaceEmbedding` | ver matriz |
| `backend/app/facial/engine.py:77` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:86` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:96` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:301` / `search_gallery_index` | F | query/ORM | `allowed_fingerprints.get` | ver matriz |
| `backend/app/facial/engine.py:212` / `replace_photo_index` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/engine.py:165` / `replace_photo_index` | F | efeito potencial | `assessment.encrypted_indicators` | ver matriz |
| `backend/app/facial/engine.py:132` / `revalidate` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:260` / `search_gallery_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/face_worker.py:37` / `record_provider_failure` | F | gate | `domain_session` | ver matriz |
| `backend/app/facial/face_worker.py:80` / `main` | F | gate | `domain_session` | ver matriz |
| `backend/app/facial/face_worker.py:156` / `processor` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/face_worker.py:205` / `main` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/face_worker.py:207` / `main` | F | produtor | `FacialEmbeddingExperimentSetting` | ver matriz |
| `backend/app/facial/face_worker.py:208` / `main` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/gemma_assets.py:48` / `prepare_gemma_model` | F | efeito potencial | `snapshot_download` | ver matriz |
| `backend/app/facial/gemma_assets.py:62` / `prepare_gemma_model` | F | efeito potencial | `(root / MARKER_NAME).write_text` | ver matriz |
| `backend/app/facial/gemma_assets.py:27` / `verify_gemma_model` | F | query/ORM | `marker.get` | ver matriz |
| `backend/app/facial/gemma_assets.py:28` / `verify_gemma_model` | F | query/ORM | `marker.get` | ver matriz |
| `backend/app/facial/gemma_provider.py:108` / `_embed_observations` | F | query/ORM | `self.last_metrics.update` | ver matriz |
| `backend/app/facial/indexing.py:110` / `enqueue_photo_index_if_eligible` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/indexing.py:198` / `enqueue_gemma_index_if_eligible` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/indexing.py:199` / `enqueue_gemma_index_if_eligible` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/indexing.py:138` / `enqueue_photo_index_if_eligible` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/indexing.py:176` / `enqueue_photo_index_if_eligible` | F | efeito potencial | `enqueue_gemma_index_if_eligible` | ver matriz |
| `backend/app/facial/indexing.py:256` / `enqueue_gallery_backfill_page` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/indexing.py:292` / `enqueue_gallery_backfill_page` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/indexing.py:305` / `enqueue_gallery_backfill_page` | F | efeito potencial | `enqueue_photo_index_if_eligible` | ver matriz |
| `backend/app/facial/indexing.py:342` / `reconcile_gallery_index` | F | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/facial/indexing.py:377` / `reconcile_automatic_gallery_policies` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/indexing.py:66` / `preview_fingerprint` | F | efeito potencial | `path.open` | ver matriz |
| `backend/app/facial/indexing.py:156` / `enqueue_photo_index_if_eligible` | F | efeito potencial | `(repository or FacialJobRepository()).enqueue` | ver matriz |
| `backend/app/facial/indexing.py:408` / `reconcile_automatic_gallery_policies` | F | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/facial/indexing.py:68` / `preview_fingerprint` | F | query/ORM | `digest.update` | ver matriz |
| `backend/app/facial/indexing.py:217` / `enqueue_gemma_index_if_eligible` | F | efeito potencial | `(repository or FacialJobRepository()).enqueue` | ver matriz |
| `backend/app/facial/indexing.py:139` / `enqueue_photo_index_if_eligible` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/indexing.py:378` / `reconcile_automatic_gallery_policies` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/indexing.py:262` / `enqueue_gallery_backfill_page` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:116` / `enqueue` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:121` / `enqueue` | F | produtor | `FacialJob` | ver matriz |
| `backend/app/facial/jobs.py:174` / `claim_next` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:313` / `_leased` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/jobs.py:314` / `_leased` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:335` / `release_denied` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:358` / `dispatch` | F | efeito potencial | `self._repository.enqueue` | ver matriz |
| `backend/app/facial/jobs.py:170` / `claim_next` | F | query/ORM | `FACIAL_JOB_KINDS_BY_CLASS.get` | ver matriz |
| `backend/app/facial/jobs.py:302` / `require_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/jobs.py:138` / `enqueue` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/jobs.py:141` / `enqueue` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:307` / `require_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/jobs.py:117` / `enqueue` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:158` / `claim_next` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:142` / `enqueue` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:335` / `release_denied` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:365` / `dispatch` | F | query/ORM | `job.get` | ver matriz |
| `backend/app/facial/jobs.py:315` / `_leased` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:44` / `analysis_for` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/lifecycle.py:48` / `analysis_for` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:53` / `admit_source` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/lifecycle.py:104` / `admit_source` | F | produtor | `PhotoAnalysis` | ver matriz |
| `backend/app/facial/lifecycle.py:119` / `admit_source` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/lifecycle.py:183` / `finalize_source` | F | efeito potencial | `FacialJobRepository().enqueue` | ver matriz |
| `backend/app/facial/lifecycle.py:198` / `finalize_source` | F | efeito potencial | `enqueue_gemma_index_if_eligible` | ver matriz |
| `backend/app/facial/lifecycle.py:208` / `write_source` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/lifecycle.py:236` / `media_can_proceed` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:258` / `cleanup_source` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/lifecycle.py:261` / `cleanup_source` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:314` / `cleanup_source` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/lifecycle.py:315` / `cleanup_source` | F | efeito potencial | `safe_source_path(photo).unlink` | ver matriz |
| `backend/app/facial/lifecycle.py:357` / `cleanup_sources` | F | efeito potencial | `cleanup_upload_fragments` | ver matriz |
| `backend/app/facial/lifecycle.py:369` / `cleanup_upload_fragments` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/lifecycle.py:66` / `admit_source` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:78` / `admit_source` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/lifecycle.py:97` / `admit_source` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/lifecycle.py:163` / `source_job_key` | F | efeito potencial | `row.expires_at.replace` | ver matriz |
| `backend/app/facial/lifecycle.py:224` / `write_source` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/lifecycle.py:225` / `write_source` | F | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/facial/lifecycle.py:227` / `write_source` | F | efeito potencial | `temporary.unlink` | ver matriz |
| `backend/app/facial/lifecycle.py:274` / `cleanup_source` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/lifecycle.py:285` / `cleanup_source` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/lifecycle.py:304` / `cleanup_source` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/lifecycle.py:323` / `cleanup_sources` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/lifecycle.py:45` / `analysis_for` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:78` / `admit_source` | F | query/ORM | `text` | ver matriz |
| `backend/app/facial/lifecycle.py:129` / `_require_source_capacity` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:134` / `_require_source_capacity` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/lifecycle.py:135` / `_require_source_capacity` | F | efeito potencial | `(root / '.pyp-uploading').glob` | ver matriz |
| `backend/app/facial/lifecycle.py:219` / `write_source` | F | efeito potencial | `temporary.open` | ver matriz |
| `backend/app/facial/lifecycle.py:286` / `cleanup_source` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/lifecycle.py:373` / `cleanup_upload_fragments` | F | gate | `require_single_tenant` | ver matriz |
| `backend/app/facial/lifecycle.py:386` / `cleanup_upload_fragments` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/lifecycle.py:391` / `cleanup_upload_fragments` | F | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/facial/lifecycle.py:262` / `cleanup_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:302` / `cleanup_source` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/lifecycle.py:369` / `cleanup_upload_fragments` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:390` / `cleanup_upload_fragments` | F | gate | `require_single_tenant` | ver matriz |
| `backend/app/facial/lifecycle.py:66` / `admit_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:275` / `cleanup_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:387` / `cleanup_upload_fragments` | F | efeito potencial | `(root / '.pyp-uploading').resolve` | ver matriz |
| `backend/app/facial/lifecycle.py:286` / `cleanup_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:237` / `media_can_proceed` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:324` / `cleanup_sources` | F | query/ORM | `select` | ver matriz |
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
| `backend/app/facial/notifications.py:45` / `enqueue_search_notification` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:52` / `enqueue_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:68` / `enqueue_search_notification` | F | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/facial/notifications.py:72` / `enqueue_search_notification` | F | produtor | `FacialSearchNotificationOutbox` | ver matriz |
| `backend/app/facial/notifications.py:108` / `process_next_search_notification` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/notifications.py:124` / `process_next_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:222` / `notification_origin` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:223` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:224` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:225` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:226` / `notification_origin` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:241` / `cancel_pending_search_notifications` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:242` / `cancel_pending_search_notifications` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/notifications.py:46` / `enqueue_search_notification` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:149` / `process_next_search_notification` | F | gate | `provider_for` | ver matriz |
| `backend/app/facial/notifications.py:162` / `process_next_search_notification` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:163` / `process_next_search_notification` | F | efeito potencial | `active_provider.send_transactional` | ver matriz |
| `backend/app/facial/notifications.py:86` / `enqueue_search_notification` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/notifications.py:89` / `enqueue_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:268` / `_notification_message` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/notifications.py:53` / `enqueue_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:226` / `notification_origin` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:243` / `cancel_pending_search_notifications` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:90` / `enqueue_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:109` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:125` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:179` / `_utc` | F | efeito potencial | `value.replace` | ver matriz |
| `backend/app/facial/observability.py:234` / `collect_facial_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/observability.py:302` / `collect_facial_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/observability.py:234` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:321` / `collect_facial_metrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/observability.py:332` / `collect_facial_metrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/observability.py:303` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:322` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:333` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/policy.py:37` / `read_policy` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/policy.py:60` / `ensure_automatic_policy` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/policy.py:105` / `ensure_automatic_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:127` / `prepare_policy` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/policy.py:157` / `prepare_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:216` / `activate_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:35` / `read_policy` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/policy.py:79` / `ensure_automatic_policy` | F | produtor | `GalleryFacialPolicy` | ver matriz |
| `backend/app/facial/policy.py:88` / `ensure_automatic_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:106` / `ensure_automatic_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:126` / `prepare_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:135` / `prepare_policy` | F | produtor | `GalleryFacialPolicy` | ver matriz |
| `backend/app/facial/policy.py:142` / `prepare_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:151` / `prepare_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:158` / `prepare_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:202` / `activate_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:217` / `activate_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:236` / `suspend_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:245` / `suspend_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:251` / `suspend_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:268` / `revoke_policy` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/policy.py:277` / `revoke_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:283` / `revoke_policy` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/policy.py:91` / `ensure_automatic_policy` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/policy.py:252` / `suspend_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:284` / `revoke_policy` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/policy.py:38` / `read_policy` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/provider.py:205` / `observe_highres_path` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/provider.py:272` / `observe_highres_path` | F | query/ORM | `self.last_metrics.update` | ver matriz |
| `backend/app/facial/provider.py:277` / `observe_highres_path` | F | query/ORM | `self.last_metrics.update` | ver matriz |
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
| `backend/app/facial/reference_store.py:34` / `delete_reference_file` | F | efeito potencial | `target.unlink` | ver matriz |
| `backend/app/facial/reference_store.py:93` / `store` | F | efeito potencial | `self._cipher.encrypt` | ver matriz |
| `backend/app/facial/reference_store.py:123` / `store` | F | efeito potencial | `self._cipher.encrypt` | ver matriz |
| `backend/app/facial/reference_store.py:106` / `store` | F | efeito potencial | `partial.write_bytes` | ver matriz |
| `backend/app/facial/reference_store.py:110` / `store` | F | efeito potencial | `os.replace` | ver matriz |
| `backend/app/facial/reference_store.py:114` / `store` | F | efeito potencial | `partial.unlink` | ver matriz |
| `backend/app/facial/reference_store.py:167` / `load` | F | efeito potencial | `self._cipher.decrypt` | ver matriz |
| `backend/app/facial/reference_store.py:193` / `delete` | F | efeito potencial | `target.unlink` | ver matriz |
| `backend/app/facial/reference_store.py:250` / `_resolve_locator` | F | efeito potencial | `self._cipher.decrypt(locator, scope=scope).decode` | ver matriz |
| `backend/app/facial/reference_store.py:206` / `_validate_jpeg` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/reference_store.py:250` / `_resolve_locator` | F | efeito potencial | `self._cipher.decrypt` | ver matriz |
| `backend/app/facial/regions.py:68` / `authorized_region` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:70` / `authorized_region` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/regions.py:87` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:90` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:91` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:102` / `region_embedding` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/regions.py:118` / `photo_regions` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:128` / `photo_regions` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/regions.py:122` / `photo_regions` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:52` / `region_query` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/regions.py:25` / `region_query` | F | query/ORM | `select` | ver matriz |
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
| `backend/app/facial/rollout.py:74` / `read_rollout` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/rollout.py:87` / `prepare_rollout` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/rollout.py:257` / `rollout_is_active` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/rollout.py:324` / `canonical_rollout_environment` | F | query/ORM | `ROLLOUT_ENVIRONMENT_ALIASES.get` | ver matriz |
| `backend/app/facial/rollout.py:341` / `_schedule_scope_shutdown` | F | efeito potencial | `enqueue_gallery_purge` | ver matriz |
| `backend/app/facial/rollout.py:367` / `_audit` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout.py:65` / `read_rollout` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/rollout.py:102` / `prepare_rollout` | F | produtor | `FacialRollout` | ver matriz |
| `backend/app/facial/rollout.py:110` / `prepare_rollout` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout.py:142` / `activate_rollout` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout.py:156` / `activate_rollout` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/rollout.py:200` / `suspend_rollout` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout.py:227` / `revoke_rollout` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout.py:268` / `rollout_is_active` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/rollout.py:368` / `_audit` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/rollout.py:67` / `read_rollout` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/rollout.py:269` / `rollout_is_active` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/rollout_operation.py:110` / `execute_protected_rollout_operation` | F | produtor | `FacialRolloutOperation` | ver matriz |
| `backend/app/facial/rollout_operation.py:123` / `execute_protected_rollout_operation` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout_operation.py:171` / `execute_protected_rollout_operation` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/rollout_operation.py:100` / `execute_protected_rollout_operation` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/rollout_operation.py:105` / `execute_protected_rollout_operation` | F | gate | `require_admin_tenant` | ver matriz |
| `backend/app/facial/rollout_operation.py:172` / `execute_protected_rollout_operation` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/rollout_operation.py:107` / `execute_protected_rollout_operation` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search.py:201` / `create_search_request` | F | produtor | `FacialSearchRequest` | ver matriz |
| `backend/app/facial/search.py:338` / `_build_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:515` / `read_latest_search_result` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:589` / `cancel_search_request` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search.py:594` / `cancel_search_request` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:634` / `reject_search_candidate` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:678` / `authorize_search_candidate_selection` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:722` / `_authorized_search_request` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:72` / `_require_search_context` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/search.py:255` / `create_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:256` / `create_search_request` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/search.py:259` / `create_search_request` | F | efeito potencial | `job_repository.enqueue` | ver matriz |
| `backend/app/facial/search.py:269` / `create_search_request` | F | efeito potencial | `job_repository.enqueue` | ver matriz |
| `backend/app/facial/search.py:279` / `create_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:320` / `_build_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:355` / `_build_snapshot` | F | produtor | `FacialSearchSnapshotItem` | ver matriz |
| `backend/app/facial/search.py:388` / `_retire_prior_searches` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:414` / `_retire_prior_searches` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search.py:419` / `_retire_prior_searches` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:429` / `_retire_prior_searches` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:487` / `read_search_result` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:574` / `cancel_search_request` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:605` / `cancel_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:647` / `reject_search_candidate` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:280` / `create_search_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:399` / `_retire_prior_searches` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:430` / `_retire_prior_searches` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:462` / `search_request_payload` | F | query/ORM | `_POLL_AFTER_MS.get` | ver matriz |
| `backend/app/facial/search.py:606` / `cancel_search_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:648` / `reject_search_candidate` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:295` / `create_search_request` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:590` / `cancel_search_request` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search.py:595` / `cancel_search_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:635` / `reject_search_candidate` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:679` / `authorize_search_candidate_selection` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:389` / `_retire_prior_searches` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:415` / `_retire_prior_searches` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search.py:420` / `_retire_prior_searches` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:339` / `_build_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:488` / `read_search_result` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:363` / `_build_snapshot` | F | query/ORM | `latest_by_photo.get` | ver matriz |
| `backend/app/facial/search.py:723` / `_authorized_search_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:516` / `read_latest_search_result` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:72` / `process_claimed_search_job` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:312` / `_request_is_authorized` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/search_worker.py:332` / `_request_is_authorized` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:333` / `_request_is_authorized` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search_worker.py:341` / `_request_is_authorized` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:439` / `_snapshot_items` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:476` / `_delete_reference` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search_worker.py:498` / `_finish_request` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/search_worker.py:516` / `_finish_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search_worker.py:526` / `_finish_request` | F | efeito potencial | `enqueue_search_notification` | ver matriz |
| `backend/app/facial/search_worker.py:226` / `process_claimed_search_job` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search_worker.py:235` / `process_claimed_search_job` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/search_worker.py:391` / `_refresh_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:443` / `_snapshot_items` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:500` / `_finish_request` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search_worker.py:507` / `_finish_request` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search_worker.py:517` / `_finish_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search_worker.py:250` / `process_claimed_search_job` | F | efeito potencial | `repository.enqueue` | ver matriz |
| `backend/app/facial/search_worker.py:278` / `process_claimed_search_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/search_worker.py:292` / `process_claimed_search_job` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:371` / `_refresh_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:417` / `_refresh_snapshot` | F | query/ORM | `latest_by_photo.get` | ver matriz |
| `backend/app/facial/search_worker.py:236` / `process_claimed_search_job` | F | produtor | `FacialSearchCandidate` | ver matriz |
| `backend/app/facial/search_worker.py:334` / `_request_is_authorized` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:227` / `process_claimed_search_job` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search_worker.py:500` / `_finish_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:507` / `_finish_request` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search_worker.py:392` / `_refresh_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:444` / `_snapshot_items` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:372` / `_refresh_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/serving.py:35` / `gallery_search_engine` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/serving.py:36` / `gallery_search_engine` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/serving.py:37` / `gallery_search_engine` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/serving.py:79` / `gallery_search_engine` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/serving.py:90` / `gallery_search_engine` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/serving.py:61` / `gallery_search_engine` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/serving.py:121` / `gallery_search_engine` | F | query/ORM | `analyses.get` | ver matriz |
| `backend/app/facial/serving.py:141` / `_utc` | F | efeito potencial | `value.replace` | ver matriz |
| `backend/app/facial/serving.py:112` / `gallery_search_engine` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/serving.py:115` / `gallery_search_engine` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/serving.py:127` / `gallery_search_engine` | F | query/ORM | `previews.get` | ver matriz |
| `backend/app/facial/serving.py:80` / `gallery_search_engine` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/serving.py:49` / `gallery_search_engine` | F | efeito potencial | `setting.worker_last_seen_at.replace` | ver matriz |
| `backend/app/facial/serving.py:91` / `gallery_search_engine` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/serving.py:112` / `gallery_search_engine` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/serving.py:115` / `gallery_search_engine` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/serving.py:62` / `gallery_search_engine` | F | query/ORM | `select` | ver matriz |
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
| `backend/app/facial/worker.py:56` / `process_claimed_index_job` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/worker.py:67` / `process_claimed_index_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/worker.py:80` / `process_claimed_index_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/worker.py:111` / `process_claimed_index_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/worker.py:112` / `process_claimed_index_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/worker.py:56` / `process_claimed_index_job` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/worker.py:120` / `process_claimed_index_job` | F | efeito potencial | `enqueue` | ver matriz |
| `backend/app/folder_processing.py:33` / `folder_settings` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/folder_processing.py:38` / `folder_settings` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:61` / `effective_preview` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:70` / `facial_processing_allowed` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing.py:79` / `configure_folder` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing.py:82` / `configure_folder` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:95` / `configure_folder` | P | produtor | `FolderProcessingSettings` | ver matriz |
| `backend/app/folder_processing.py:96` / `configure_folder` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/folder_processing.py:104` / `configure_folder` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_processing.py:34` / `folder_settings` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:58` / `effective_preview` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:112` / `configure_folder` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing.py:128` / `configure_folder` | P | efeito potencial | `enqueue` | ver matriz |
| `backend/app/folder_processing.py:104` / `configure_folder` | P | query/ORM | `update` | ver matriz |
| `backend/app/folder_processing.py:82` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:106` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:113` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:46` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/folder_processing_api.py:38` / `folder_or_404` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing_api.py:41` / `folder_or_404` | P | query/ORM | `db.get` | ver matriz |
| `backend/app/folder_processing_api.py:60` / `configuration` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:53` / `configuration` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing_api.py:125` / `enqueue_folder_preview` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:151` / `reprocess_folder_facial` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:153` / `reprocess_folder_facial` | P | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/folder_processing_api.py:89` / `configuration` | P | query/ORM | `preview_counts.get` | ver matriz |
| `backend/app/folder_processing_api.py:126` / `enqueue_folder_preview` | P | efeito potencial | `enqueue_preview` | ver matriz |
| `backend/app/folder_processing_api.py:55` / `configuration` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_processing_api.py:53` / `configuration` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:121` / `enqueue_folder_preview` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:148` / `reprocess_folder_facial` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:60` / `configuration` | P | query/ORM | `select` | ver matriz |
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
| `backend/app/global_pix.py:71` / `global_pix_settings` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/global_pix.py:72` / `global_pix_settings` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/global_pix.py:31` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:55` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:56` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:99` / `pix_payload` | K | query/ORM | `result.update` | ver matriz |
| `backend/app/global_pix.py:120` / `apply_configuration` | K | produtor | `GlobalPixSettings` | ver matriz |
| `backend/app/global_pix.py:121` / `apply_configuration` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/global_pix.py:135` / `proposal_preview` | K | produtor | `GlobalPixSettings` | ver matriz |
| `backend/app/global_pix.py:32` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:33` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
| `backend/app/global_pix.py:46` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:48` / `normalize_configuration` | K | query/ORM | `fields.get` | ver matriz |
| `backend/app/global_pix.py:113` / `apply_configuration` | K | gate | `require_admin_tenant` | ver matriz |
| `backend/app/global_pix.py:72` / `global_pix_settings` | K | query/ORM | `select` | ver matriz |
| `backend/app/global_pix.py:57` / `normalize_configuration` | K | query/ORM | `configuration.get` | ver matriz |
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
| `backend/app/homolog_cleanup.py:224` / `execute` | L | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `backend/app/homolog_cleanup.py:225` / `execute` | L | query/ORM | `schema_map.get` | ver matriz |
| `backend/app/homolog_cleanup.py:229` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:230` / `execute` | L | gate | `require_single_tenant` | ver matriz |
| `backend/app/homolog_cleanup.py:243` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:244` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:245` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:248` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:253` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:254` / `execute` | L | gate | `require_single_tenant` | ver matriz |
| `backend/app/homolog_cleanup.py:229` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:233` / `execute` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:235` / `execute` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:247` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:253` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:110` / `_count` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:113` / `_count` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:210` / `_clear_media_root` | L | efeito potencial | `entry.unlink` | ver matriz |
| `backend/app/homolog_cleanup.py:247` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:274` / `operational_delete_order` | L | query/ORM | `targets.add` | ver matriz |
| `backend/app/homolog_cleanup.py:243` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:244` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:245` / `execute` | L | query/ORM | `update` | ver matriz |
| `backend/app/homolog_cleanup.py:248` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:233` / `execute` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:235` / `execute` | L | query/ORM | `select` | ver matriz |
| `backend/app/infinitepay_settings.py:55` / `load_configuration` | K | gate | `require_active_owner` | ver matriz |
| `backend/app/infinitepay_settings.py:56` / `load_configuration` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/infinitepay_settings.py:86` / `apply_proposal` | K | gate | `require_security_owner` | ver matriz |
| `backend/app/infinitepay_settings.py:93` / `apply_proposal` | K | produtor | `InfinitePaySettings` | ver matriz |
| `backend/app/infinitepay_settings.py:94` / `apply_proposal` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/infinitepay_settings.py:91` / `apply_proposal` | K | query/ORM | `proposed.get` | ver matriz |
| `backend/app/infinitepay_settings.py:56` / `load_configuration` | K | query/ORM | `select` | ver matriz |
| `backend/app/installation_operator.py:14` / `operator_is_active` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/installation_operator.py:21` / `require_operator` | O | gate | `operator_is_active` | ver matriz |
| `backend/app/installation_operator.py:14` / `operator_is_active` | O | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1247` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:1289` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:1351` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2141` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2151` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2213` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2219` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2240` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2257` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2343` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2625` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2637` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2717` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2782` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2843` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2854` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2867` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2934` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2990` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3053` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3065` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:3190` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3209` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3411` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3520` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3569` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3662` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:3677` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3729` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3829` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3968` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3980` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4053` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4219` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4242` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4312` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4445` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4616` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4687` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4722` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4767` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4861` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5159` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5249` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5362` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5457` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5489` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5538` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5598` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5783` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6129` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:6226` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6358` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6454` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6476` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6691` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6706` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6730` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6758` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6788` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6927` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7007` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7040` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7254` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7283` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7319` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7430` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7508` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7542` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7607` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7876` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7895` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7969` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8013` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8086` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8305` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:8372` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:8424` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8479` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8613` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8726` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8772` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8801` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8827` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8853` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9190` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9247` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9333` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:9363` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:9391` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9610` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9646` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9658` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9683` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9713` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9766` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9814` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9942` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9967` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10144` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10266` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10323` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10362` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10488` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10508` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10530` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10559` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10640` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10754` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10782` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10867` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10949` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10977` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:11005` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:11073` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11086` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11175` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11591` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11639` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:11667` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11706` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11721` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11740` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12353` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12373` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12479` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:12533` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12557` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:12580` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12605` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:514` / `read_bounded_body` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:942` / `directory_tenant_id` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:949` / `require_same_origin` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:978` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:979` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:988` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1007` / `require_parent_gallery_mutable` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1021` / `require_derived_gallery_mutable` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1030` / `assigned_photo_for_gallery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:1031` / `assigned_photo_for_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1046` / `assigned_photo_for_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1120` / `_client_journey_destination` | X | query/ORM | `private_by_parent.get` | ver matriz |
| `backend/app/main.py:1137` / `statistics_data` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:1254` / `whatsapp_webhook` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1255` / `whatsapp_webhook` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1291` / `admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1310` / `update_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1320` / `refresh_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1332` / `pair_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1357` / `admin_whatsapp_deliveries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1385` / `retry_admin_whatsapp_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1386` / `retry_admin_whatsapp_delivery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1448` / `validate_client_capability_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1489` / `client_challenge_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1510` / `_active_client_reauthentication_parent` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1618` / `client_resend` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1624` / `client_resend` | X | efeito potencial | `resend_client_challenge` | ver matriz |
| `backend/app/main.py:1639` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1911` / `admin_password` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1939` / `admin_totp` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1952` / `admin_totp` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1987` / `admin_recovery_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2065` / `admin_recovery_reset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2099` / `confirm_admin_email` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2112` / `confirm_admin_email` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2161` / `authenticated_identity` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2169` / `authenticated_identity` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2222` / `admin_email_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2280` / `admin_global_pix_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2317` / `admin_global_pix_confirm` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2318` / `admin_global_pix_confirm` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2368` / `admin_infinitepay_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2397` / `_infinitepay_challenge_for_session` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2398` / `_infinitepay_challenge_for_session` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2630` / `public_branding` | X | gate | `branding_tenant_id` | ver matriz |
| `backend/app/main.py:2633` / `public_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2641` / `admin_branding` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2642` / `admin_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2651` / `update_admin_branding` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2652` / `update_admin_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2666` / `update_visual_protection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2667` / `update_visual_protection` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2693` / `upload_branding_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2702` / `upload_branding_asset` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:2703` / `upload_branding_asset` | X | efeito potencial | `temporary.write_bytes` | ver matriz |
| `backend/app/main.py:2704` / `upload_branding_asset` | X | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/main.py:2705` / `upload_branding_asset` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2724` / `public_branding_asset` | X | gate | `branding_tenant_id` | ver matriz |
| `backend/app/main.py:2727` / `public_branding_asset` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2749` / `public_branding_asset` | X | query/ORM | `{'.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon'}.get` | ver matriz |
| `backend/app/main.py:2787` / `admin_validation_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2860` / `admin_capacity_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2875` / `admin_facial_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2888` / `admin_facial_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2938` / `admin_facial_engine_experiment` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2940` / `admin_facial_engine_experiment` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2952` / `update_admin_facial_engine_experiment` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2955` / `update_admin_facial_engine_experiment` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2998` / `admin_clients` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3009` / `create_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3015` / `create_client` | X | produtor | `Client` | ver matriz |
| `backend/app/main.py:3016` / `create_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3018` / `create_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3043` / `update_client_name` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3044` / `update_client_name` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3057` / `get_client_deletion_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3059` / `get_client_deletion_inventory` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3069` / `delete_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3194` / `admin_parent_galleries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3196` / `admin_parent_galleries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3219` / `parent_gallery_overview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3223` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3272` / `_parent_gallery_or_404` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3308` / `_active_gallery_capability` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3319` / `_gallery_cover_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3339` / `_cover_preview_url` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3351` / `_cover_derivative` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3359` / `_client_preview_derivative` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3383` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3384` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3393` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3399` / `_cover_assets_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:3406` / `_cover_assets_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3416` / `parent_gallery_editor` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3524` / `parent_gallery_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3554` / `update_parent_gallery_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3573` / `parent_gallery_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3603` / `parent_gallery_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3634` / `set_parent_gallery_cover` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3637` / `set_parent_gallery_cover` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3668` / `clear_parent_gallery_cover` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3681` / `parent_gallery_sales` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3709` / `update_parent_gallery_sales` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3733` / `parent_gallery_details` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3793` / `register_parent_gallery_cover_photo` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3802` / `register_parent_gallery_cover_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3835` / `admin_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3854` / `prepare_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3885` / `activate_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3924` / `suspend_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3949` / `revoke_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3974` / `admin_parent_gallery_facial_cleanup_proof` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3988` / `admin_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4057` / `admin_private_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4131` / `retry_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4170` / `reprocess_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4223` / `admin_parent_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4227` / `admin_parent_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4249` / `admin_parent_gallery_available_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4320` / `admin_parent_gallery_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4404` / `create_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4409` / `create_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4417` / `create_photo_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:4425` / `create_photo_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4435` / `_admin_linked_gallery_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4450` / `admin_client_restricted_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4503` / `create_admin_client_restricted_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4512` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4515` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4528` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4533` / `create_admin_client_restricted_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:4539` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4541` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4559` / `grant_restricted_folder_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4561` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4574` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4624` / `revoke_restricted_folder_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4626` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4627` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4636` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4647` / `revoke_restricted_folder_client` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4654` / `revoke_restricted_folder_client` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:4667` / `rename_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4669` / `rename_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4691` / `delete_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4693` / `delete_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4696` / `delete_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4715` / `delete_photo_folder` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:4716` / `delete_photo_folder` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:4727` / `admin_photo_folder_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4738` / `admin_photo_folder_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4775` / `delete_folder_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4777` / `delete_folder_photo_asset` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4780` / `delete_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4798` / `delete_folder_photo_asset` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:4806` / `_delete_photo_records` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:4825` / `_delete_photo_records` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4828` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4829` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4830` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4831` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4832` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4835` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4836` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4837` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4838` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4847` / `_delete_photo_records` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:4870` / `delete_folder_photo_assets` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4872` / `delete_folder_photo_assets` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4903` / `register_folder_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4905` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4928` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4942` / `register_folder_photo_asset` | X | produtor | `PhotoAsset` | ver matriz |
| `backend/app/main.py:4951` / `register_folder_photo_asset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4963` / `_publish_photo_folder` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:5031` / `publish_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5033` / `publish_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5043` / `publish_photo_folder` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:5054` / `publish_parent_gallery_ready_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5087` / `release_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5097` / `release_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5107` / `release_photo_folder` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:5114` / `create_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5116` / `create_parent_gallery` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:5118` / `create_parent_gallery` | X | produtor | `ParentGallery` | ver matriz |
| `backend/app/main.py:5119` / `create_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5163` / `parent_gallery_public_link_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5195` / `issue_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5225` / `rotate_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5256` / `revoke_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5311` / `issue_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5314` / `issue_parent_gallery_client_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5338` / `rotate_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5372` / `revoke_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5391` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:5464` / `parent_gallery_deletion_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5499` / `parent_gallery_client_unlink_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5502` / `parent_gallery_client_unlink_inventory` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5503` / `parent_gallery_client_unlink_inventory` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5547` / `delete_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5555` / `delete_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5572` / `delete_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5579` / `delete_parent_gallery` | X | produtor | `GalleryLifecycleOperation` | ver matriz |
| `backend/app/main.py:5591` / `delete_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5602` / `gallery_lifecycle_operation_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5604` / `gallery_lifecycle_operation_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5616` / `retry_gallery_lifecycle_operation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5618` / `retry_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5645` / `cancel_gallery_lifecycle_operation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5647` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5717` / `clone_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5735` / `challenge_client_phone` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5736` / `challenge_client_phone` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5747` / `challenge_client_phone` | X | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/main.py:5755` / `change_client_phone` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5756` / `change_client_phone` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5760` / `change_client_phone` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:5787` / `parent_gallery_clients` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5954` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5968` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6069` / `link_admin_client_to_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6099` / `update_admin_client_gallery_access` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6102` / `update_admin_client_gallery_access` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6108` / `update_admin_client_gallery_access` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6142` / `unlink_admin_client_from_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6150` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6167` / `unlink_admin_client_from_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6168` / `unlink_admin_client_from_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6171` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6181` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6199` / `unlink_admin_client_from_parent_gallery` | X | produtor | `GalleryLifecycleOperation` | ver matriz |
| `backend/app/main.py:6219` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6233` / `selection_detail` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6235` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6248` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6323` / `_selection_html_preview` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:6324` / `_selection_html_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6341` / `_selection_html_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6366` / `export_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6370` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6434` / `export_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6457` / `export_finalized_order` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6459` / `export_finalized_order` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6462` / `export_finalized_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6484` / `export_canonical_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6488` / `export_canonical_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6489` / `export_canonical_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6490` / `export_canonical_selection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6576` / `register_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6590` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6592` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6607` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6638` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6657` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6685` / `import_photo_source` | X | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/main.py:6696` / `photo_media_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6700` / `photo_media_status` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6710` / `admin_photo_facial_analysis` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6736` / `admin_photo_preview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6737` / `admin_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6740` / `admin_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6764` / `admin_watermarked_photo_preview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6765` / `admin_watermarked_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6768` / `admin_watermarked_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6796` / `admin_purchase_history` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6873` / `_pricing_preset_payload` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:6906` / `_replace_pricing_preset_tiers` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:6907` / `_replace_pricing_preset_tiers` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6913` / `_replace_pricing_preset_tiers` | X | query/ORM | `db.add_all` | ver matriz |
| `backend/app/main.py:6933` / `list_progressive_pricing_presets` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6949` / `create_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6951` / `create_progressive_pricing_preset` | X | produtor | `ProgressivePricingPreset` | ver matriz |
| `backend/app/main.py:6974` / `_pricing_preset_or_404` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6987` / `update_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7013` / `deactivate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7029` / `activate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7047` / `simulate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7238` / `save_parent_pricing` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7239` / `save_parent_pricing` | X | query/ORM | `db.add_all` | ver matriz |
| `backend/app/main.py:7258` / `admin_parent_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7271` / `save_admin_parent_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7287` / `admin_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7289` / `admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7292` / `admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7309` / `save_admin_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7325` / `admin_gallery_orders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7327` / `admin_gallery_orders` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7392` / `create_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7394` / `create_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7395` / `create_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7436` / `private_gallery_link_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7452` / `private_gallery_link_status` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7481` / `issue_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7498` / `rotate_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7515` / `revoke_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7517` / `revoke_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7536` / `rotate_private_gallery_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7551` / `revoke_private_gallery_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7618` / `private_gallery_members` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7620` / `private_gallery_members` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7626` / `private_gallery_members` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7681` / `add_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7684` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7685` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7775` / `_change_private_member_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7812` / `_change_private_member_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7813` / `_change_private_member_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7845` / `block_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7864` / `unblock_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7883` / `unlink_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7911` / `admin_gallery_membership_notifications` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7961` / `read_admin_gallery_membership_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7972` / `list_private_upload_batches` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7975` / `list_private_upload_batches` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7985` / `begin_private_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8000` / `finish_private_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8017` / `admin_private_gallery_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8062` / `create_private_gallery_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8065` / `create_private_gallery_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8071` / `create_private_gallery_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:8079` / `create_private_gallery_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:8090` / `admin_private_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8092` / `admin_private_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8292` / `add_admin_private_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8312` / `remove_admin_private_gallery_photo` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8315` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8342` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8376` / `delete_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8378` / `delete_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8382` / `delete_derived_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8386` / `delete_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8401` / `delete_derived_gallery` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:8437` / `list_derived_galleries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8483` / `derived_gallery_detail` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8485` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8489` / `derived_gallery_detail` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8494` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8495` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8557` / `update_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8574` / `renew_gallery_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8588` / `_reopening_request_payload` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8621` / `list_gallery_reopening_requests` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8668` / `decide_gallery_reopening_request` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8670` / `decide_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8709` / `retry_gallery_reopening_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8710` / `retry_gallery_reopening_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8741` / `admin_statistics` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8777` / `admin_statistics_filters` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8812` / `export_selected_not_purchased_txt` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8838` / `export_purchased_txt` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8899` / `client_library` | X | query/ORM | `parent_ids.update` | ver matriz |
| `backend/app/main.py:9014` / `client_library` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9184` / `_commerce_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9338` / `remove_unified_cart_group` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9368` / `remove_unified_cart_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9584` / `_historical_item_for_client` | X | gate | `client_tenant_id` | ver matriz |
| `backend/app/main.py:9585` / `_historical_item_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9598` / `_historical_item_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9617` / `client_purchased_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9631` / `client_purchased_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9632` / `client_purchased_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9777` / `gallery_released_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9852` / `gallery_review` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9953` / `client_gallery_cover_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9976` / `client_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9989` / `client_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10019` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10161` / `unselect_photo_from_public_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10290` / `public_gallery_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10448` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:10804` / `public_gallery_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10850` / `favorite_canonical_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10880` / `unfavorite_canonical_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10902` / `record_canonical_photo_view` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10935` / `create_canonical_photo_comment` | X | produtor | `PhotoComment` | ver matriz |
| `backend/app/main.py:10942` / `create_canonical_photo_comment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10965` / `canonical_client_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10987` / `remove_canonical_comment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11065` / `_canonical_cart_payload` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:11096` / `client_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11127` / `request_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11140` / `request_gallery_reopening` | X | produtor | `GalleryReopeningRequest` | ver matriz |
| `backend/app/main.py:11146` / `request_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11148` / `request_gallery_reopening` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:11149` / `request_gallery_reopening` | X | produtor | `GalleryReopeningNotificationOutbox` | ver matriz |
| `backend/app/main.py:11155` / `request_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11187` / `canonical_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11210` / `request_canonical_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11217` / `request_canonical_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11227` / `request_canonical_gallery_reopening` | X | produtor | `GalleryReopeningRequest` | ver matriz |
| `backend/app/main.py:11233` / `request_canonical_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11235` / `request_canonical_gallery_reopening` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:11236` / `request_canonical_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11266` / `checkout_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11298` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11307` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11325` / `communicate_payment` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11335` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11349` / `communicate_payment` | X | produtor | `PaymentCommunication` | ver matriz |
| `backend/app/main.py:11355` / `communicate_payment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11358` / `communicate_payment` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:11393` / `decide_payment_communication` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11402` / `decide_payment_communication` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11415` / `decide_payment_communication` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11442` / `correct_payment_confirmation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11449` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11461` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11468` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11485` / `correct_payment_confirmation` | X | query/ORM | `{'confirmed': 'confirmed', 'refused': 'cancelled'}.get` | ver matriz |
| `backend/app/main.py:11498` / `correct_payment_confirmation` | X | produtor | `PaymentConfirmationCorrection` | ver matriz |
| `backend/app/main.py:11507` / `correct_payment_confirmation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11556` / `update_order_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11572` / `resend_order_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11597` / `push_subscription_state` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11646` / `unregister_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11649` / `unregister_push_subscription` | X | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/main.py:11669` / `list_notification_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11710` / `list_payment_templates` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11732` / `admin_removed_photo_movements` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11758` / `list_payment_communications` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:12335` / `retry_payment_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:12336` / `retry_payment_notification` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:12381` / `client_pending_order` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12454` / `favorite_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:12460` / `favorite_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12488` / `unfavorite_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12513` / `create_photo_comment` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:12519` / `create_photo_comment` | X | produtor | `PhotoComment` | ver matriz |
| `backend/app/main.py:12526` / `create_photo_comment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:12540` / `client_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12564` / `remove_own_comment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12584` / `admin_comments` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:12588` / `admin_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12612` / `remove_comment_as_admin` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:12614` / `remove_comment_as_admin` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:913` / `db_session` | X | gate | `domain_session` | ver matriz |
| `backend/app/main.py:931` / `require_installation_operator` | X | gate | `require_operator` | ver matriz |
| `backend/app/main.py:937` / `directory_tenant_id` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1085` / `_client_journey_destination` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1088` / `_client_journey_destination` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1102` / `_client_journey_destination` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1116` / `_client_journey_destination` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1168` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1189` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1193` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1209` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1214` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1268` / `whatsapp_webhook` | X | gate | `webhook_owner` | ver matriz |
| `backend/app/main.py:1293` / `admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1452` / `validate_client_capability_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1476` / `client_challenge_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1595` / `client_challenge` | X | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/main.py:1619` / `client_resend` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1659` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1724` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1869` / `client_verify` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:1923` / `admin_password` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:1945` / `admin_totp` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:2024` / `admin_recovery_resend` | X | efeito potencial | `resend_security_challenge` | ver matriz |
| `backend/app/main.py:2071` / `admin_recovery_reset` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2105` / `confirm_admin_email` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2156` / `authenticated_identity` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2186` / `logout` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2187` / `logout` | X | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/main.py:2190` / `logout` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2451` / `admin_infinitepay_resend` | X | efeito potencial | `resend_security_challenge` | ver matriz |
| `backend/app/main.py:2544` / `admin_email_change_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2609` / `_branding_payload` | X | query/ORM | `payload.update` | ver matriz |
| `backend/app/main.py:2671` / `update_visual_protection` | X | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/main.py:2674` / `update_visual_protection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2697` / `upload_branding_asset` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:2742` / `public_branding_asset` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:2789` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2793` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2794` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2903` / `_facial_embedding_experiment_payload` | X | efeito potencial | `worker_seen.replace` | ver matriz |
| `backend/app/main.py:2907` / `_facial_embedding_experiment_payload` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2972` / `update_admin_facial_engine_experiment` | X | produtor | `FacialEmbeddingExperimentSetting` | ver matriz |
| `backend/app/main.py:2973` / `update_admin_facial_engine_experiment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3019` / `create_client` | X | produtor | `ClientPhone` | ver matriz |
| `backend/app/main.py:3180` / `_client_deletion_transaction_state` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3316` / `_gallery_cover_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3420` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3433` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3441` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3577` / `parent_gallery_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3586` / `parent_gallery_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3646` / `set_parent_gallery_cover` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3736` / `parent_gallery_details` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3739` / `parent_gallery_details` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3742` / `parent_gallery_details` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3810` / `register_parent_gallery_cover_photo` | X | produtor | `PhotoAsset` | ver matriz |
| `backend/app/main.py:3819` / `register_parent_gallery_cover_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3855` / `prepare_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3886` / `activate_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3925` / `suspend_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3950` / `revoke_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4061` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4066` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4080` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4088` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4225` / `admin_parent_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4253` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4322` / `admin_parent_gallery_folders` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4325` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4346` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4457` / `admin_client_restricted_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4469` / `admin_client_restricted_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4474` / `admin_client_restricted_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4520` / `create_admin_client_restricted_folder` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:4524` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4541` / `create_admin_client_restricted_folder` | X | produtor | `FolderClientGrant` | ver matriz |
| `backend/app/main.py:4579` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4586` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4596` / `grant_restricted_folder_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4642` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4706` / `delete_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4732` / `admin_photo_folder_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4741` / `admin_photo_folder_photos` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4818` / `_delete_photo_records` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4880` / `delete_folder_photo_assets` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4932` / `register_folder_photo_asset` | X | efeito potencial | `namespaced_upload_key` | ver matriz |
| `backend/app/main.py:4934` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4939` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4954` / `register_folder_photo_asset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4970` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5058` / `publish_parent_gallery_ready_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5068` / `publish_parent_gallery_ready_photos` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:5417` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:5519` / `parent_gallery_client_unlink_inventory` | X | efeito potencial | `client_unlink_inventory` | ver matriz |
| `backend/app/main.py:5678` / `cancel_gallery_lifecycle_operation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5718` / `clone_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5791` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5798` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5803` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5888` / `parent_gallery_clients` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5918` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5936` / `parent_gallery_clients` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:5975` / `parent_gallery_clients` | X | query/ORM | `clients_by_id.get` | ver matriz |
| `backend/app/main.py:5976` / `parent_gallery_clients` | X | query/ORM | `galleries_by_client.get` | ver matriz |
| `backend/app/main.py:5977` / `parent_gallery_clients` | X | query/ORM | `memberships_by_client.get` | ver matriz |
| `backend/app/main.py:5978` / `parent_gallery_clients` | X | query/ORM | `registrations_by_client.get` | ver matriz |
| `backend/app/main.py:5989` / `parent_gallery_clients` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:5991` / `parent_gallery_clients` | X | query/ORM | `phone_verification_by_client.get` | ver matriz |
| `backend/app/main.py:6006` / `parent_gallery_clients` | X | query/ORM | `latest_canonical_order_by_client.get` | ver matriz |
| `backend/app/main.py:6020` / `parent_gallery_clients` | X | query/ORM | `last_access_by_client.get` | ver matriz |
| `backend/app/main.py:6113` / `update_admin_client_gallery_access` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:6119` / `update_admin_client_gallery_access` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6252` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6260` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6268` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6290` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6396` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6440` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6494` / `export_canonical_selection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6547` / `export_canonical_selection` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6645` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6670` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6681` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6698` / `photo_media_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6712` / `admin_photo_facial_analysis` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6803` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6813` / `admin_purchase_history` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6817` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6875` / `_pricing_preset_payload` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6957` / `create_progressive_pricing_preset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:7050` / `simulate_progressive_pricing_preset` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7095` / `pricing_payload` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7311` / `save_admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7329` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7483` / `issue_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7500` / `rotate_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7537` / `rotate_private_gallery_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7552` / `revoke_private_gallery_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7568` / `_private_member_payload` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7689` / `add_private_gallery_member` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7694` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7751` / `add_private_gallery_member` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:7822` / `_change_private_member_status` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:7846` / `block_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7865` / `unblock_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7884` / `unlink_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7922` / `admin_gallery_membership_notifications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8021` / `admin_private_gallery_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8240` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8293` / `add_admin_private_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8323` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8334` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:8349` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:8352` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8360` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:8396` / `delete_derived_gallery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8411` / `gallery_operational_status` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8413` / `gallery_operational_status` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8440` / `list_derived_galleries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8446` / `list_derived_galleries` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8457` / `list_derived_galleries` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8499` / `derived_gallery_detail` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8510` / `derived_gallery_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8627` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8679` / `decide_gallery_reopening_request` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8680` / `decide_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8779` / `admin_statistics_filters` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8781` / `admin_statistics_filters` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8787` / `admin_statistics_filters` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8860` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8870` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8916` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:8919` / `client_library` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:8939` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8960` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:8963` / `client_library` | X | query/ORM | `registrations_by_parent.get` | ver matriz |
| `backend/app/main.py:9019` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9028` / `client_library` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:9040` / `client_library` | X | query/ORM | `prepared_gallery_ids.update` | ver matriz |
| `backend/app/main.py:9050` / `client_library` | X | query/ORM | `prepared_gallery_ids.update` | ver matriz |
| `backend/app/main.py:9090` / `client_library` | X | query/ORM | `public_by_parent.get` | ver matriz |
| `backend/app/main.py:9091` / `client_library` | X | query/ORM | `private_by_parent.get` | ver matriz |
| `backend/app/main.py:9112` / `client_library` | X | query/ORM | `canonical_cart_groups.get` | ver matriz |
| `backend/app/main.py:9122` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:9271` / `infinitepay_return` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9354` / `remove_unified_cart_group` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9399` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9476` / `client_purchase_history` | X | query/ORM | `operational_galleries.get` | ver matriz |
| `backend/app/main.py:9477` / `client_purchase_history` | X | query/ORM | `canonical_parents.get` | ver matriz |
| `backend/app/main.py:9562` / `client_purchase_history` | X | query/ORM | `order_payload.get` | ver matriz |
| `backend/app/main.py:9725` / `gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9832` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9858` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9866` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9874` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9999` / `client_photo_preview` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10038` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10132` / `_operational_gallery_for_public_client` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:10661` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10677` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10694` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10856` / `favorite_canonical_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10886` / `unfavorite_canonical_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:10910` / `record_canonical_photo_view` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11035` / `unselect_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11036` / `unselect_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11236` / `request_canonical_gallery_reopening` | X | produtor | `GalleryReopeningNotificationOutbox` | ver matriz |
| `backend/app/main.py:11456` / `correct_payment_confirmation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11476` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11576` / `resend_order_delivery` | X | efeito potencial | `resend_delivery` | ver matriz |
| `backend/app/main.py:11617` / `register_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11643` / `unregister_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11789` / `list_payment_communications` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:11809` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11970` / `list_payment_communications` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:11971` / `list_payment_communications` | X | query/ORM | `communications_by_order.get` | ver matriz |
| `backend/app/main.py:11978` / `list_payment_communications` | X | query/ORM | `card_payments.get` | ver matriz |
| `backend/app/main.py:12004` / `list_payment_communications` | X | query/ORM | `items_by_order.get` | ver matriz |
| `backend/app/main.py:12404` / `client_pending_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12468` / `favorite_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:12496` / `unfavorite_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:12586` / `admin_comments` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:492` / `validate_branding_asset` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:1138` / `statistics_data` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1279` / `whatsapp_admin_payload` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:1322` / `refresh_admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1335` / `pair_admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1373` / `admin_whatsapp_deliveries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1404` / `retry_admin_whatsapp_delivery` | X | efeito potencial | `updated_at.replace` | ver matriz |
| `backend/app/main.py:2226` / `admin_email_channel` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:2249` / `admin_security_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2284` / `admin_global_pix_challenge` | X | query/ORM | `configuration.get` | ver matriz |
| `backend/app/main.py:2670` / `update_visual_protection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3071` / `delete_client` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:3229` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3232` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3238` / `parent_gallery_overview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3900` / `activate_parent_gallery_facial_policy` | X | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/main.py:4268` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4339` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4358` / `admin_parent_gallery_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4591` / `grant_restricted_folder_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4596` / `grant_restricted_folder_client` | X | produtor | `FolderClientGrant` | ver matriz |
| `backend/app/main.py:4855` / `_remove_photo_files` | X | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/main.py:4954` / `register_folder_photo_asset` | X | produtor | `PrivateUploadBatchAsset` | ver matriz |
| `backend/app/main.py:4966` / `_publish_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4974` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4997` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5430` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:5549` / `delete_parent_gallery` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:5682` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `(operation.manifest or {}).get` | ver matriz |
| `backend/app/main.py:5683` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5830` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5848` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5852` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5877` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5979` / `parent_gallery_clients` | X | query/ORM | `projections.get` | ver matriz |
| `backend/app/main.py:5990` / `parent_gallery_clients` | X | query/ORM | `canonical_selected.get` | ver matriz |
| `backend/app/main.py:6007` / `parent_gallery_clients` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:6072` / `link_admin_client_to_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6144` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:6280` / `selection_detail` | X | query/ORM | `sales_by_photo.get` | ver matriz |
| `backend/app/main.py:6384` / `export_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6503` / `export_canonical_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6602` / `import_photo_source` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:6815` / `admin_purchase_history` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6915` / `_replace_pricing_preset_tiers` | X | produtor | `ProgressivePricingTier` | ver matriz |
| `backend/app/main.py:6934` / `list_progressive_pricing_presets` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7241` / `save_parent_pricing` | X | produtor | `PriceRule` | ver matriz |
| `backend/app/main.py:7337` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7578` / `_private_member_payload` | X | efeito potencial | `membership.unlinked_at.isoformat` | ver matriz |
| `backend/app/main.py:7627` / `private_gallery_members` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7912` / `admin_gallery_membership_notifications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8095` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8102` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8116` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8126` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8142` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8152` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8328` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8335` / `remove_admin_private_gallery_photo` | X | produtor | `DerivedGalleryPhotoOrigin` | ver matriz |
| `backend/app/main.py:8623` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8902` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8907` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9077` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9093` / `client_library` | X | query/ORM | `galleries_by_id.get` | ver matriz |
| `backend/app/main.py:9109` / `client_library` | X | query/ORM | `carts_by_gallery.get` | ver matriz |
| `backend/app/main.py:9116` / `client_library` | X | query/ORM | `orders_by_gallery.get` | ver matriz |
| `backend/app/main.py:9118` / `client_library` | X | query/ORM | `canonical_orders_by_parent.get` | ver matriz |
| `backend/app/main.py:9431` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9445` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9460` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9470` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9480` / `client_purchase_history` | X | query/ORM | `history_by_item.get` | ver matriz |
| `backend/app/main.py:9792` / `gallery_released_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10000` / `client_photo_preview` | X | produtor | `PhotoView` | ver matriz |
| `backend/app/main.py:10444` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:10445` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:10856` / `favorite_canonical_photo` | X | produtor | `PhotoFavorite` | ver matriz |
| `backend/app/main.py:10910` / `record_canonical_photo_view` | X | produtor | `PhotoView` | ver matriz |
| `backend/app/main.py:11161` / `request_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11247` / `request_canonical_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11369` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11418` / `decide_payment_communication` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11524` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11714` / `list_payment_templates` | X | query/ORM | `configured.get` | ver matriz |
| `backend/app/main.py:11823` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11843` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11864` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11902` / `list_payment_communications` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:11935` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11999` / `list_payment_communications` | X | query/ORM | `scopes_by_communication.get` | ver matriz |
| `backend/app/main.py:12166` / `list_payment_communications` | X | query/ORM | `configured_templates.get` | ver matriz |
| `backend/app/main.py:12188` / `list_payment_communications` | X | query/ORM | `delivery_counts.get` | ver matriz |
| `backend/app/main.py:12469` / `favorite_photo` | X | produtor | `PhotoFavorite` | ver matriz |
| `backend/app/main.py:1448` / `validate_client_capability_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1510` / `_active_client_reauthentication_parent` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1694` / `client_verify` | X | produtor | `Client` | ver matriz |
| `backend/app/main.py:1699` / `client_verify` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:1701` / `client_verify` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:1731` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1911` / `admin_password` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1987` / `admin_recovery_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2066` / `admin_recovery_reset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2100` / `confirm_admin_email` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2113` / `confirm_admin_email` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2162` / `authenticated_identity` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2761` / `public_branding_asset` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:2851` / `admin_installation_capabilities` | X | gate | `operator_is_active` | ver matriz |
| `backend/app/main.py:2912` / `_facial_embedding_experiment_payload` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3044` / `update_client_name` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3240` / `parent_gallery_overview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4279` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4591` / `grant_restricted_folder_client` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:4603` / `grant_restricted_folder_client` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4647` / `revoke_restricted_folder_client` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4729` / `admin_photo_folder_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4837` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4838` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4928` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5690` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `previous_state.get` | ver matriz |
| `backend/app/main.py:5736` / `challenge_client_phone` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5756` / `change_client_phone` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5882` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5898` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5909` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5944` / `parent_gallery_clients` | X | query/ORM | `canonical_item_counts.get` | ver matriz |
| `backend/app/main.py:5948` / `parent_gallery_clients` | X | query/ORM | `canonical_group_scopes.get` | ver matriz |
| `backend/app/main.py:6206` / `unlink_admin_client_from_parent_gallery` | X | efeito potencial | `client_unlink_inventory` | ver matriz |
| `backend/app/main.py:6626` / `import_photo_source` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:6646` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:6806` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6908` / `_replace_pricing_preset_tiers` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6938` / `list_progressive_pricing_presets` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7163` / `save_parent_pricing` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7238` / `save_parent_pricing` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:7796` / `_change_private_member_status` | X | efeito potencial | `unlink_private_membership` | ver matriz |
| `backend/app/main.py:8031` / `admin_private_gallery_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8045` / `admin_private_gallery_folders` | X | query/ORM | `counts.get` | ver matriz |
| `backend/app/main.py:8195` / `admin_private_gallery_photos` | X | query/ORM | `state_priority.get` | ver matriz |
| `backend/app/main.py:8589` / `_reopening_request_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8636` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8643` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8889` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9099` / `client_library` | X | query/ORM | `public_row.get` | ver matriz |
| `backend/app/main.py:9104` / `client_library` | X | query/ORM | `private_row.get` | ver matriz |
| `backend/app/main.py:9423` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9599` / `_historical_item_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9741` / `gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9884` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10667` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10683` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10708` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10721` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11597` / `push_subscription_state` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11794` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11805` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11976` / `list_payment_communications` | X | query/ORM | `notifications_by_communication.get` | ver matriz |
| `backend/app/main.py:1085` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1089` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1103` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1140` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1184` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1203` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1452` / `validate_client_capability_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1702` / `client_verify` | X | produtor | `ClientPhone` | ver matriz |
| `backend/app/main.py:1781` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2190` / `logout` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2545` / `admin_email_change_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2675` / `update_visual_protection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2789` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2793` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2802` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2807` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2810` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2818` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2822` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2862` / `admin_capacity_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:3300` / `_active_gallery_capability` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4081` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4089` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4487` / `admin_client_restricted_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4818` / `_delete_photo_records` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4934` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5696` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `previous_state.get` | ver matriz |
| `backend/app/main.py:5925` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6037` / `parent_gallery_clients` | X | query/ORM | `canonical_purchased.get` | ver matriz |
| `backend/app/main.py:6040` / `parent_gallery_clients` | X | query/ORM | `canonical_reopening.get` | ver matriz |
| `backend/app/main.py:6043` / `parent_gallery_clients` | X | query/ORM | `finalized_by_client.get` | ver matriz |
| `backend/app/main.py:6044` / `parent_gallery_clients` | X | query/ORM | `canonical_financial_by_client.get` | ver matriz |
| `backend/app/main.py:6297` / `selection_detail` | X | query/ORM | `sales_by_photo.get` | ver matriz |
| `backend/app/main.py:6671` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6798` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8196` / `admin_private_gallery_photos` | X | query/ORM | `commercial_state_by_photo_client.get` | ver matriz |
| `backend/app/main.py:8217` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:8225` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:8233` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:8256` / `admin_private_gallery_photos` | X | query/ORM | `origins_by_reference.get` | ver matriz |
| `backend/app/main.py:8411` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8413` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9042` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:9052` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:9271` / `infinitepay_return` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10048` / `select_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10467` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11995` / `list_payment_communications` | X | query/ORM | `notifications_by_communication.get` | ver matriz |
| `backend/app/main.py:11996` / `list_payment_communications` | X | query/ORM | `corrections_by_communication.get` | ver matriz |
| `backend/app/main.py:1032` / `assigned_photo_for_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1489` / `client_challenge_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1807` / `client_verify` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:1939` / `admin_totp` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2170` / `authenticated_identity` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2280` / `admin_global_pix_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2317` / `admin_global_pix_confirm` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2318` / `admin_global_pix_confirm` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2368` / `admin_infinitepay_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2397` / `_infinitepay_challenge_for_session` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2398` / `_infinitepay_challenge_for_session` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2670` / `update_visual_protection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3340` / `_cover_preview_url` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3351` / `_cover_derivative` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3360` / `_client_preview_derivative` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3385` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3394` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3803` / `register_parent_gallery_cover_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4410` / `create_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4435` / `_admin_linked_gallery_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4528` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4574` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4636` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4828` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4829` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4830` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4831` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4832` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4836` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:5853` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6033` / `parent_gallery_clients` | X | query/ORM | `restricted_available.get` | ver matriz |
| `backend/app/main.py:6325` / `_selection_html_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6342` / `_selection_html_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6435` / `export_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6490` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6638` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6659` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:6700` / `photo_media_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6741` / `admin_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6769` / `admin_watermarked_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7374` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7453` / `private_gallery_link_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8066` / `create_private_gallery_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8206` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8316` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8343` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8711` / `retry_gallery_reopening_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9165` / `client_library` | X | query/ORM | `canonical_orders_by_parent.get` | ver matriz |
| `backend/app/main.py:9338` / `remove_unified_cart_group` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9368` / `remove_unified_cart_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9575` / `client_purchase_history` | X | query/ORM | `item.get` | ver matriz |
| `backend/app/main.py:9586` / `_historical_item_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10020` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10048` / `select_photo` | X | produtor | `PhotoSelection` | ver matriz |
| `backend/app/main.py:10052` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10161` / `unselect_photo_from_public_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10850` / `favorite_canonical_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10880` / `unfavorite_canonical_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10902` / `record_canonical_photo_view` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10987` / `remove_canonical_comment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11299` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11450` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12382` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12461` / `favorite_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12489` / `unfavorite_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12565` / `remove_own_comment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12615` / `remove_comment_as_admin` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:937` / `directory_tenant_id` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1194` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1215` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1358` / `admin_whatsapp_deliveries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1476` / `client_challenge_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2907` / `_facial_embedding_experiment_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3181` / `_client_deletion_transaction_state` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3578` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3647` / `set_parent_gallery_cover` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3742` / `parent_gallery_details` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4062` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4067` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4469` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4586` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4642` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4741` / `admin_photo_folder_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4939` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4970` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5792` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5799` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5804` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6253` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6261` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6595` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:6645` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6806` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6817` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6876` / `_pricing_preset_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7051` / `simulate_progressive_pricing_preset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7096` / `pricing_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7690` / `add_private_gallery_member` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8241` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8324` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8353` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8440` / `list_derived_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8511` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8779` / `admin_statistics_filters` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8787` / `admin_statistics_filters` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8883` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9354` / `remove_unified_cart_group` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9423` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9721` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9774` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9828` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10039` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10434` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11037` / `unselect_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11794` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1047` / `assigned_photo_for_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1800` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2807` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3197` / `admin_parent_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3224` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3229` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3233` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3383` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4228` / `admin_parent_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4269` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4512` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4515` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4561` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4626` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4627` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4650` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4696` / `delete_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4780` / `delete_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4833` / `_delete_photo_records` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4835` / `_delete_photo_records` | X | query/ORM | `update` | ver matriz |
| `backend/app/main.py:4905` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4975` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4998` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5504` / `parent_gallery_client_unlink_inventory` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5556` / `delete_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5619` / `retry_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5648` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5684` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5848` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5877` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5954` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5968` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6102` / `update_admin_client_gallery_access` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6108` / `update_admin_client_gallery_access` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6151` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6182` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6462` / `export_finalized_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6657` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7337` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7626` / `private_gallery_members` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7975` / `list_private_upload_batches` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8329` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8382` / `delete_derived_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8490` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8671` / `decide_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8903` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8908` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9446` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9461` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9471` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9618` / `client_purchased_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9977` / `client_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9990` / `client_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10290` / `public_gallery_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10805` / `public_gallery_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10965` / `canonical_client_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11097` / `client_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11128` / `request_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11187` / `canonical_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11210` / `request_canonical_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11217` / `request_canonical_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11308` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11336` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11370` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11419` / `decide_payment_communication` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11462` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11469` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11525` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12541` / `client_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12589` / `admin_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2912` / `_facial_embedding_experiment_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3421` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3434` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3442` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4280` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4326` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4579` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4603` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4733` / `admin_photo_folder_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5059` / `publish_parent_gallery_ready_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5888` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5918` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6269` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6494` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7164` / `save_parent_pricing` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7330` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8022` / `admin_private_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8458` / `list_derived_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8500` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8637` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8643` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8680` / `decide_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8782` / `admin_statistics_filters` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8861` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8871` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8890` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9019` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9163` / `client_library` | X | query/ORM | `cart.get` | ver matriz |
| `backend/app/main.py:9400` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9530` / `client_purchase_history` | X | query/ORM | `communications_by_order.get` | ver matriz |
| `backend/app/main.py:9859` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9867` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9875` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10661` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10677` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11477` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11805` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11809` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12405` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1280` / `whatsapp_admin_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2227` / `admin_email_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2802` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2811` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2818` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2823` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3604` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4340` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4487` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4967` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5572` / `delete_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5831` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6172` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8117` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8127` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8143` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9043` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9432` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11162` / `request_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11247` / `request_canonical_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11824` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11844` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11865` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11936` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2794` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3587` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4254` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4457` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4706` / `delete_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5882` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6548` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8032` / `admin_private_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8207` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8396` / `delete_derived_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9742` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9885` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10052` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10668` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10684` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10709` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10722` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11767` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4359` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5925` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6385` / `export_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6504` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8103` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9053` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9078` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9407` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9410` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9793` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4347` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4474` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5909` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7375` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2231` / `admin_email_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3320` / `_gallery_cover_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8096` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8153` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9778` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5898` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8940` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9726` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9833` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11877` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7628` / `private_gallery_members` | X | query/ORM | `select` | ver matriz |
| `backend/app/media.py:43` / `safe_source_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:49` / `safe_source_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:57` / `safe_derivative_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:63` / `safe_derivative_path` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:121` / `_watermark_font_size` | P | query/ORM | `{'horizontal': inner_width, 'vertical': inner_height, 'diagonal': hypot(inner_width, inner_height)}.get` | ver matriz |
| `backend/app/media.py:160` / `watermark` | P | query/ORM | `{'horizontal': 0, 'vertical': 90, 'diagonal': 35}.get` | ver matriz |
| `backend/app/media.py:170` / `watermark` | P | query/ORM | `{'sans-serif': 'DejaVuSans.ttf', 'serif': 'DejaVuSerif.ttf', 'monospace': 'DejaVuSansMono.ttf', 'DejaVuSans': 'DejaVuSans.ttf', 'DejaVuSerif': 'DejaVuSerif.ttf'}.get` | ver matriz |
| `backend/app/media.py:223` / `watermark` | P | query/ORM | `layer_draw.text` | ver matriz |
| `backend/app/media.py:228` / `watermark` | P | query/ORM | `{'left': margin, 'center': (marked.width - layer.width) // 2, 'right': marked.width - layer.width - margin}.get` | ver matriz |
| `backend/app/media.py:233` / `watermark` | P | query/ORM | `{'top': margin, 'middle': (marked.height - layer.height) // 2, 'bottom': marked.height - layer.height - margin}.get` | ver matriz |
| `backend/app/media.py:246` / `require_media_photo` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:261` / `enqueue_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:262` / `enqueue_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:288` / `generate_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:423` / `save_presentation_jpeg` | P | efeito potencial | `destination.write_bytes` | ver matriz |
| `backend/app/media.py:217` / `watermark` | P | query/ORM | `layer_draw.text` | ver matriz |
| `backend/app/media.py:247` / `require_media_photo` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:248` / `require_media_photo` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:249` / `require_media_photo` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:268` / `enqueue_derivatives` | P | produtor | `MediaJob` | ver matriz |
| `backend/app/media.py:269` / `enqueue_derivatives` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/media.py:291` / `generate_derivatives` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:299` / `generate_derivatives` | P | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/media.py:306` / `generate_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:320` / `generate_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:366` / `generate_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:370` / `generate_derivatives` | P | gate | `owned_record` | ver matriz |
| `backend/app/media.py:396` / `generate_derivatives` | P | efeito potencial | `enqueue_after_derivatives` | ver matriz |
| `backend/app/media.py:274` / `enqueue_derivatives` | P | query/ORM | `db.get` | ver matriz |
| `backend/app/media.py:321` / `generate_derivatives` | P | efeito potencial | `Image.open` | ver matriz |
| `backend/app/media.py:387` / `generate_derivatives` | P | efeito potencial | `enqueue_photo_index_if_eligible` | ver matriz |
| `backend/app/media.py:263` / `enqueue_derivatives` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:338` / `generate_derivatives` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/media.py:342` / `generate_derivatives` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:345` / `generate_derivatives` | P | gate | `media_namespace` | ver matriz |
| `backend/app/media.py:357` / `generate_derivatives` | P | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/media.py:306` / `generate_derivatives` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:353` / `generate_derivatives` | P | gate | `require_media_photo` | ver matriz |
| `backend/app/media.py:359` / `generate_derivatives` | P | produtor | `MediaDerivative` | ver matriz |
| `backend/app/media.py:360` / `generate_derivatives` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/media.py:355` / `generate_derivatives` | P | efeito potencial | `temporary.unlink` | ver matriz |
| `backend/app/media.py:320` / `generate_derivatives` | P | query/ORM | `select` | ver matriz |
| `backend/app/media.py:338` / `generate_derivatives` | P | query/ORM | `select` | ver matriz |
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
| `backend/app/notification_delivery.py:66` / `mirror_payment_projection` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:77` / `recipient_allowed` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_delivery.py:324` / `retry_payment_projection` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_delivery.py:325` / `retry_payment_projection` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:328` / `retry_payment_projection` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:53` / `utc` | N | efeito potencial | `value.replace` | ver matriz |
| `backend/app/notification_delivery.py:82` / `recipient_allowed` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:95` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:118` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:122` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:139` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:198` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:206` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:224` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:308` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:333` / `retry_payment_projection` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_delivery.py:96` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:102` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:103` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:152` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:160` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:170` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:183` / `process_next_notification` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_delivery.py:194` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:216` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:225` / `process_next_notification` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:239` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:66` / `mirror_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:90` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:166` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:219` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:325` / `retry_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:86` / `recipient_allowed` | N | gate | `require_admin_tenant` | ver matriz |
| `backend/app/notification_delivery.py:253` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:259` / `process_next_notification` | N | efeito potencial | `push_sender or send_push` | ver matriz |
| `backend/app/notification_delivery.py:264` / `process_next_notification` | N | gate | `provider_for` | ver matriz |
| `backend/app/notification_delivery.py:268` / `process_next_notification` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:280` / `process_next_notification` | N | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/notification_delivery.py:299` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:170` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:254` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:259` / `process_next_notification` | N | efeito potencial | `decrypt_subscription` | ver matriz |
| `backend/app/notification_delivery.py:275` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:123` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:206` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:308` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:333` / `retry_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:103` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:219` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:275` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:299` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:183` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:198` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:46` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:47` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:66` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:99` / `record_restricted_folder_ready` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:121` / `record_restricted_folder_ready` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_events.py:139` / `record_payment_event` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_events.py:142` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:160` / `record_payment_event` | N | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/notification_events.py:35` / `legacy_owned_photographer_phone` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_events.py:58` / `record_gallery_milestone` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_events.py:122` / `record_restricted_folder_ready` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:125` / `record_restricted_folder_ready` | N | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/notification_events.py:143` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:144` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:150` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:173` / `record_payment_event` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_events.py:70` / `record_gallery_milestone` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_events.py:72` / `record_gallery_milestone` | N | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/notification_events.py:145` / `record_payment_event` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_events.py:155` / `record_payment_event` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_events.py:176` / `record_payment_event` | N | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/notification_events.py:178` / `record_payment_event` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_events.py:70` / `record_gallery_milestone` | N | produtor | `NotificationMilestone` | ver matriz |
| `backend/app/notification_events.py:86` / `record_gallery_milestone` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_events.py:178` / `record_payment_event` | N | produtor | `PaymentNotificationOutbox` | ver matriz |
| `backend/app/notification_events.py:58` / `record_gallery_milestone` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:173` / `record_payment_event` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:77` / `record_gallery_milestone` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_events.py:102` / `record_restricted_folder_ready` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:155` / `record_payment_event` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_events.py:77` / `record_gallery_milestone` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:73` / `setting_for` | K | gate | `require_identity_tenant` | ver matriz |
| `backend/app/notification_settings.py:76` / `setting_for` | K | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_settings.py:81` / `setting_for` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:100` / `payment_template_bodies` | K | gate | `require_identity_tenant` | ver matriz |
| `backend/app/notification_settings.py:101` / `payment_template_bodies` | K | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_settings.py:130` / `save_setting` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:172` / `enqueue_event` | K | gate | `require_identity_tenant` | ver matriz |
| `backend/app/notification_settings.py:190` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:84` / `setting_for` | K | query/ORM | `DEFAULT_PAYMENT_TEMPLATES.get` | ver matriz |
| `backend/app/notification_settings.py:87` / `setting_for` | K | produtor | `NotificationSetting` | ver matriz |
| `backend/app/notification_settings.py:89` / `setting_for` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:92` / `setting_for` | K | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_settings.py:135` / `save_setting` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:146` / `save_setting` | K | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_settings.py:182` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:187` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:198` / `enqueue_event` | K | produtor | `NotificationEvent` | ver matriz |
| `backend/app/notification_settings.py:208` / `enqueue_event` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:239` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:59` / `render_text` | K | query/ORM | `values.get` | ver matriz |
| `backend/app/notification_settings.py:81` / `setting_for` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:155` / `save_setting` | K | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_settings.py:175` / `enqueue_event` | K | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_settings.py:190` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:103` / `payment_template_bodies` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:212` / `enqueue_event` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:220` / `enqueue_event` | K | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_settings.py:101` / `payment_template_bodies` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:130` / `save_setting` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:182` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:187` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:212` / `enqueue_event` | K | produtor | `NotificationDelivery` | ver matriz |
| `backend/app/notification_settings.py:226` / `enqueue_event` | K | query/ORM | `db.add` | ver matriz |
| `backend/app/notification_settings.py:239` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:175` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:226` / `enqueue_event` | K | produtor | `NotificationDelivery` | ver matriz |
| `backend/app/notification_settings.py:146` / `save_setting` | K | query/ORM | `update` | ver matriz |
| `backend/app/notification_settings.py:220` / `enqueue_event` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:155` / `save_setting` | K | query/ORM | `update` | ver matriz |
| `backend/app/notification_settings.py:148` / `save_setting` | K | query/ORM | `select` | ver matriz |
| `backend/app/notification_settings.py:157` / `save_setting` | K | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:67` / `lock_delivery_order` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/order_delivery.py:68` / `lock_delivery_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:72` / `lock_delivery_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:73` / `lock_delivery_order` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:86` / `record_delivery_notice` | S | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/order_delivery.py:133` / `resend_delivery` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:142` / `delivery_notice_allowed` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/order_delivery.py:151` / `delivery_notice_allowed` | S | query/ORM, efeito potencial | `{'order-delivery': 3, 'order-delivery-resend': 4}.get` | ver matriz |
| `backend/app/order_delivery.py:94` / `record_delivery_notice` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/order_delivery.py:105` / `set_delivery` | S | gate | `require_admin_tenant` | ver matriz |
| `backend/app/order_delivery.py:125` / `resend_delivery` | S | gate | `require_admin_tenant` | ver matriz |
| `backend/app/order_delivery.py:68` / `lock_delivery_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:133` / `resend_delivery` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:72` / `lock_delivery_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:94` / `record_delivery_notice` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:142` / `delivery_notice_allowed` | S | query/ORM | `select` | ver matriz |
| `backend/app/order_delivery.py:73` / `lock_delivery_order` | S | query/ORM | `select` | ver matriz |
| `backend/app/ownership_schema.py:69` / `apply_ownership_constraints` | X | query/ORM | `metadata.info.get` | ver matriz |
| `backend/app/parent_registration.py:21` / `link_client_to_parent` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/parent_registration.py:22` / `link_client_to_parent` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/parent_registration.py:25` / `link_client_to_parent` | G | gate | `require_client_owner` | ver matriz |
| `backend/app/parent_registration.py:27` / `link_client_to_parent` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/parent_registration.py:40` / `link_client_to_parent` | G | produtor | `ParentGalleryRegistration` | ver matriz |
| `backend/app/parent_registration.py:46` / `link_client_to_parent` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/parent_registration.py:49` / `link_client_to_parent` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/parent_registration.py:28` / `link_client_to_parent` | G | query/ORM | `select` | ver matriz |
| `backend/app/parent_registration.py:50` / `link_client_to_parent` | G | query/ORM | `select` | ver matriz |
| `backend/app/payment_provider.py:217` / `check_payment` | K | query/ORM | `data.get` | ver matriz |
| `backend/app/payment_provider.py:218` / `check_payment` | K | query/ORM | `data.get` | ver matriz |
| `backend/app/payment_provider.py:222` / `check_payment` | K | query/ORM | `data.get` | ver matriz |
| `backend/app/payment_provider.py:223` / `check_payment` | K | query/ORM | `data.get` | ver matriz |
| `backend/app/payment_provider.py:165` / `__init__` | K | produtor | `httpx.Client` | ver matriz |
| `backend/app/payment_provider.py:184` / `create_checkout` | K | query/ORM | `data.get` | ver matriz |
| `backend/app/payment_templates.py:23` / `validate_template` | K | efeito potencial | `body.replace('\r\n', '\n').replace` | ver matriz |
| `backend/app/payment_templates.py:23` / `validate_template` | K | efeito potencial | `body.replace` | ver matriz |
| `backend/app/preview_adjustment/api.py:33` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:64` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:83` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:164` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/preview_adjustment/api.py:72` / `galleries` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/api.py:105` / `gallery_progress` | P | query/ORM | `counts.update` | ver matriz |
| `backend/app/preview_adjustment/api.py:135` / `enqueue_gallery` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:37` / `configuration` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:57` / `save_configuration` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:92` / `gallery_progress` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:154` / `enqueue_gallery` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/preview_adjustment/api.py:173` / `compare` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/api.py:119` / `gallery_progress` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/api.py:155` / `enqueue_gallery` | P | efeito potencial | `enqueue` | ver matriz |
| `backend/app/preview_adjustment/api.py:168` / `compare` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/api.py:105` / `gallery_progress` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/api.py:174` / `compare` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:96` / `gallery_progress` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:73` / `galleries` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:107` / `gallery_progress` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/api.py:142` / `enqueue_gallery` | P | query/ORM | `select` | ver matriz |
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
| `backend/app/preview_adjustment/service.py:58` / `settings` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:65` / `settings` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:72` / `configure` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:74` / `configure` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:124` / `inputs` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:127` / `inputs` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:143` / `inputs` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:162` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:172` / `adjustment_for` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:173` / `adjustment_for` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:181` / `private_facial_job_completed` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:196` / `enqueue` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:197` / `enqueue` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:216` / `enqueue` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:275` / `adjusted_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:280` / `adjusted_path` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:81` / `configure` | P | produtor | `GalleryPreviewSettings` | ver matriz |
| `backend/app/preview_adjustment/service.py:89` / `configure` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/preview_adjustment/service.py:99` / `configure` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:166` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:200` / `enqueue` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:225` / `enqueue` | P | produtor | `PreviewAdjustment` | ver matriz |
| `backend/app/preview_adjustment/service.py:226` / `enqueue` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/preview_adjustment/service.py:236` / `enqueue_after_derivatives` | P | efeito potencial | `enqueue` | ver matriz |
| `backend/app/preview_adjustment/service.py:276` / `adjusted_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:290` / `presentation_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:327` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:328` / `process_one` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:330` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:347` / `process_one` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:59` / `settings` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:130` / `inputs` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/preview_adjustment/service.py:160` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:297` / `presentation_path` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:303` / `presentation_path` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:366` / `process_one` | P | produtor | `BrandingSettings` | ver matriz |
| `backend/app/preview_adjustment/service.py:385` / `process_one` | P | efeito potencial | `Image.open` | ver matriz |
| `backend/app/preview_adjustment/service.py:394` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:395` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:403` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:406` / `process_one` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:424` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:433` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:434` / `process_one` | P | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/preview_adjustment/service.py:316` / `process_one` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:400` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:404` / `process_one` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:457` / `process_one` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:444` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:445` / `process_one` | P | efeito potencial | `previous.unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:452` / `process_one` | P | efeito potencial | `output.with_suffix('.tmp').unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:453` / `process_one` | P | efeito potencial | `output.unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:75` / `configure` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:144` / `inputs` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:173` / `adjustment_for` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:197` / `enqueue` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:396` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:100` / `configure` | P | query/ORM | `update` | ver matriz |
| `backend/app/preview_adjustment/service.py:131` / `inputs` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:182` / `private_facial_job_completed` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:403` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:401` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:458` / `process_one` | P | query/ORM | `update` | ver matriz |
| `backend/app/preview_adjustment/service.py:331` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:105` / `configure` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:317` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:65` / `_insert_once` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:88` / `ensure_private_photo_reference` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:89` / `ensure_private_photo_reference` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:108` / `ensure_private_photo_reference` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:135` / `derive_client_selection` | G | gate | `client_tenant_id` | ver matriz |
| `backend/app/private_derivation.py:137` / `derive_client_selection` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:138` / `derive_client_selection` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:139` / `derive_client_selection` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:140` / `derive_client_selection` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:236` / `derive_admin_gallery` | G | gate | `client_tenant_id` | ver matriz |
| `backend/app/private_derivation.py:238` / `derive_admin_gallery` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:239` / `derive_admin_gallery` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_derivation.py:100` / `ensure_private_photo_reference` | G | produtor | `DerivedGalleryPhoto` | ver matriz |
| `backend/app/private_derivation.py:113` / `ensure_private_photo_reference` | G | produtor | `DerivedGalleryPhotoOrigin` | ver matriz |
| `backend/app/private_derivation.py:148` / `derive_client_selection` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:209` / `derive_client_selection` | G | produtor | `PhotoSelection` | ver matriz |
| `backend/app/private_derivation.py:69` / `_insert_once` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_derivation.py:93` / `ensure_private_photo_reference` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:73` / `_insert_once` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_derivation.py:118` / `ensure_private_photo_reference` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:202` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:141` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:149` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_derivation.py:137` / `derive_client_selection` | G | query/ORM | `select` | ver matriz |
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
| `backend/app/private_membership.py:53` / `membership_for_client` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:97` / `operational_galleries_for_client` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_membership.py:111` / `client_has_operational_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:112` / `client_has_operational_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:115` / `client_has_operational_membership` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:124` / `client_has_operational_membership` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:139` / `_legacy_gallery_for_client` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_membership.py:199` / `ensure_private_membership` | G | gate | `require_client_owner` | ver matriz |
| `backend/app/private_membership.py:82` / `operational_galleries_for_client` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_membership.py:209` / `ensure_private_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:46` / `membership_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:90` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:163` / `_create_legacy_compatible_gallery` | G | produtor | `DerivedGallery` | ver matriz |
| `backend/app/private_membership.py:174` / `_create_legacy_compatible_gallery` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_membership.py:235` / `ensure_private_membership` | G | produtor | `DerivedGalleryMembership` | ver matriz |
| `backend/app/private_membership.py:242` / `ensure_private_membership` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_membership.py:262` / `ensure_private_membership` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_membership.py:116` / `client_has_operational_membership` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:125` / `client_has_operational_membership` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:140` / `_legacy_gallery_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:45` / `membership_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:68` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:86` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_membership.py:64` / `operational_galleries_for_client` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:28` / `batch_for` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:29` / `batch_for` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_upload_batches.py:56` / `create_batch` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:57` / `create_batch` | G | produtor | `PrivateUploadBatch` | ver matriz |
| `backend/app/private_upload_batches.py:58` / `create_batch` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/private_upload_batches.py:84` / `process_ready_batches` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_upload_batches.py:40` / `batch_payload` | G | query/ORM | `db.execute` | ver matriz |
| `backend/app/private_upload_batches.py:71` / `close_batch` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/private_upload_batches.py:90` / `process_ready_batches` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:93` / `process_ready_batches` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/private_upload_batches.py:105` / `process_ready_batches` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_upload_batches.py:120` / `process_ready_batches` | G | gate | `require_active_owner` | ver matriz |
| `backend/app/private_upload_batches.py:68` / `close_batch` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_upload_batches.py:106` / `process_ready_batches` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_upload_batches.py:51` / `batch_payload` | G | efeito potencial | `logical_upload_key` | ver matriz |
| `backend/app/private_upload_batches.py:91` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:96` / `process_ready_batches` | G | query/ORM | `db.scalars` | ver matriz |
| `backend/app/private_upload_batches.py:110` / `process_ready_batches` | G | gate | `owned_record` | ver matriz |
| `backend/app/private_upload_batches.py:113` / `process_ready_batches` | G | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/private_upload_batches.py:93` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:29` / `batch_for` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:68` / `close_batch` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:79` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:40` / `batch_payload` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:96` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/private_upload_batches.py:84` / `process_ready_batches` | G | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:45` / `prepare_provider_payment` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/provider_checkout.py:46` / `prepare_provider_payment` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/provider_checkout.py:49` / `prepare_provider_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_checkout.py:50` / `prepare_provider_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_checkout.py:78` / `prepare_provider_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_checkout.py:99` / `prepare_provider_payment` | S | produtor | `ProviderPayment` | ver matriz |
| `backend/app/provider_checkout.py:105` / `prepare_provider_payment` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/provider_checkout.py:151` / `prepare_provider_payment` | S | produtor | `ProviderPaymentAttempt` | ver matriz |
| `backend/app/provider_checkout.py:153` / `prepare_provider_payment` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/provider_checkout.py:194` / `issue_provider_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_checkout.py:197` / `issue_provider_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_checkout.py:68` / `prepare_provider_payment` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_checkout.py:110` / `prepare_provider_payment` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_checkout.py:118` / `prepare_provider_payment` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_checkout.py:146` / `prepare_provider_payment` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/provider_checkout.py:160` / `checkout_request_for` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_checkout.py:170` / `checkout_request_for` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_checkout.py:261` / `_restore_local_selection` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_checkout.py:131` / `prepare_provider_payment` | S | query/ORM | `by_key.get` | ver matriz |
| `backend/app/provider_checkout.py:131` / `prepare_provider_payment` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/provider_checkout.py:176` / `checkout_request_for` | S | query/ORM | `grouped.get` | ver matriz |
| `backend/app/provider_checkout.py:266` / `_restore_local_selection` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_checkout.py:273` / `_restore_local_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_checkout.py:279` / `_restore_local_selection` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/provider_checkout.py:146` / `prepare_provider_payment` | S | query/ORM | `delete` | ver matriz |
| `backend/app/provider_checkout.py:170` / `checkout_request_for` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:279` / `_restore_local_selection` | S | produtor | `PhotoSelection` | ver matriz |
| `backend/app/provider_checkout.py:49` / `prepare_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:50` / `prepare_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:78` / `prepare_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:194` / `issue_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:197` / `issue_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:266` / `_restore_local_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:273` / `_restore_local_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:68` / `prepare_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:110` / `prepare_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:160` / `checkout_request_for` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:261` / `_restore_local_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_checkout.py:118` / `prepare_provider_payment` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:48` / `apply_payment_check` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:49` / `apply_payment_check` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:52` / `apply_payment_check` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:53` / `apply_payment_check` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/provider_confirmation.py:54` / `apply_payment_check` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:74` / `apply_payment_check` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:139` / `apply_payment_check` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:178` / `apply_payment_check` | S | efeito potencial | `enqueue_event` | ver matriz |
| `backend/app/provider_confirmation.py:209` / `place_payment_hold` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:210` / `place_payment_hold` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:213` / `place_payment_hold` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:214` / `place_payment_hold` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/provider_confirmation.py:220` / `place_payment_hold` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:225` / `place_payment_hold` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:241` / `place_payment_hold` | S | produtor | `ProviderPaymentCorrection` | ver matriz |
| `backend/app/provider_confirmation.py:251` / `place_payment_hold` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/provider_confirmation.py:261` / `place_payment_hold` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:82` / `apply_payment_check` | S | produtor | `ProviderPaymentReceipt` | ver matriz |
| `backend/app/provider_confirmation.py:93` / `apply_payment_check` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/provider_confirmation.py:146` / `apply_payment_check` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_confirmation.py:159` / `apply_payment_check` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provider_confirmation.py:234` / `place_payment_hold` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provider_confirmation.py:266` / `place_payment_hold` | S | query/ORM | `db.query(NotificationDelivery).filter(NotificationDelivery.tenant_id == tenant_id, NotificationDelivery.event_id == event.id, NotificationDelivery.status.in_(('queued', 'processing'))).update` | ver matriz |
| `backend/app/provider_confirmation.py:48` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:49` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:209` / `place_payment_hold` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:210` / `place_payment_hold` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:216` / `place_payment_hold` | S | gate | `require_admin_tenant` | ver matriz |
| `backend/app/provider_confirmation.py:225` / `place_payment_hold` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:261` / `place_payment_hold` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:159` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:52` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:74` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:139` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:213` / `place_payment_hold` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:266` / `place_payment_hold` | S | query/ORM | `db.query` | ver matriz |
| `backend/app/provider_confirmation.py:54` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:220` / `place_payment_hold` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:146` / `apply_payment_check` | S | query/ORM | `select` | ver matriz |
| `backend/app/provider_confirmation.py:234` / `place_payment_hold` | S | query/ORM | `select` | ver matriz |
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
| `backend/app/provision_photographer.py:50` / `existing_admin_owner` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/provision_photographer.py:60` / `plan_provisioning` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/provision_photographer.py:71` / `plan_provisioning` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/provision_photographer.py:110` / `provision_photographer` | A | produtor | `AdminUser` | ver matriz |
| `backend/app/provision_photographer.py:113` / `provision_photographer` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/provision_photographer.py:38` / `existing_admin_by_email` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provision_photographer.py:45` / `existing_admin_owner` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/provision_photographer.py:67` / `plan_provisioning` | A | gate | `existing_admin_owner` | ver matriz |
| `backend/app/provision_photographer.py:94` / `provision_photographer` | A | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `backend/app/provision_photographer.py:101` / `provision_photographer` | A | query/ORM | `db.execute` | ver matriz |
| `backend/app/provision_photographer.py:108` / `provision_photographer` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/provision_photographer.py:112` / `provision_photographer` | A | produtor | `TenantAdmin` | ver matriz |
| `backend/app/provision_photographer.py:98` / `provision_photographer` | A | query/ORM | `translation.get` | ver matriz |
| `backend/app/provision_photographer.py:101` / `provision_photographer` | A | query/ORM | `text` | ver matriz |
| `backend/app/provision_photographer.py:108` / `provision_photographer` | A | produtor | `Tenant` | ver matriz |
| `backend/app/provision_photographer.py:81` / `validate_new_credentials` | A | efeito potencial | `totp_secret.replace` | ver matriz |
| `backend/app/provision_photographer.py:71` / `plan_provisioning` | A | query/ORM | `select` | ver matriz |
| `backend/app/provision_photographer.py:38` / `existing_admin_by_email` | A | query/ORM | `select` | ver matriz |
| `backend/app/provision_photographer.py:45` / `existing_admin_owner` | A | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:59` / `active_capability_by_id` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:69` / `active_registration` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:136` / `apply_public_gallery_access` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/public_gallery_access.py:139` / `apply_public_gallery_access` | G | gate | `owned_record` | ver matriz |
| `backend/app/public_gallery_access.py:206` / `require_public_gallery_browsing` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:278` / `authorized_canonical_photo` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:53` / `active_capability_by_id` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/public_gallery_access.py:109` / `client_otp_delivery_allowed` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:206` / `require_public_gallery_browsing` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:222` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:245` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:252` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:60` / `active_capability_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:70` / `active_registration` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:109` / `client_otp_delivery_allowed` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:219` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:227` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
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
| `backend/app/storage_metrics.py:105` / `measure_owned_photo_storage` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/storage_metrics.py:108` / `measure_owned_photo_storage` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/storage_metrics.py:111` / `measure_owned_photo_storage` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/storage_metrics.py:115` / `measure_owned_photo_storage` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/storage_metrics.py:109` / `measure_owned_photo_storage` | X | query/ORM | `paths.add` | ver matriz |
| `backend/app/storage_metrics.py:110` / `measure_owned_photo_storage` | X | query/ORM | `paths.update` | ver matriz |
| `backend/app/storage_metrics.py:114` / `measure_owned_photo_storage` | X | query/ORM | `paths.add` | ver matriz |
| `backend/app/storage_metrics.py:116` / `measure_owned_photo_storage` | X | query/ORM | `paths.update` | ver matriz |
| `backend/app/storage_metrics.py:120` / `measure_owned_photo_storage` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/storage_metrics.py:108` / `measure_owned_photo_storage` | X | query/ORM | `select` | ver matriz |
| `backend/app/storage_metrics.py:111` / `measure_owned_photo_storage` | X | query/ORM | `select` | ver matriz |
| `backend/app/storage_metrics.py:115` / `measure_owned_photo_storage` | X | query/ORM | `select` | ver matriz |
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
| `backend/app/tenancy.py:34` / `require_admin_tenant` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:42` / `require_parent_tenant` | A | gate | `owned_record` | ver matriz |
| `backend/app/tenancy.py:50` / `bind_domain_owner` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:67` / `_remember_changed_owners` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:17` / `require_single_tenant` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenancy.py:24` / `require_admin_tenant` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenancy.py:51` / `bind_domain_owner` | A | query/ORM | `db.info.setdefault('tenant_domain_owners', set()).add` | ver matriz |
| `backend/app/tenancy.py:61` / `domain_session` | A | gate | `enable_domain_guard` | ver matriz |
| `backend/app/tenancy.py:76` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:82` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:83` / `_revalidate_domain_commit` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/tenancy.py:86` / `_revalidate_domain_commit` | A | query/ORM | `db.info.get` | ver matriz |
| `backend/app/tenancy.py:87` / `_revalidate_domain_commit` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/tenancy.py:83` / `_revalidate_domain_commit` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:17` / `require_single_tenant` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:24` / `require_admin_tenant` | A | query/ORM | `select` | ver matriz |
| `backend/app/tenancy.py:87` / `_revalidate_domain_commit` | A | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:53` / `communications_for_orders` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/unified_checkout.py:59` / `communications_for_orders` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:82` / `_materials` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:113` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:147` / `cart_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:226` / `cart_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:232` / `cart_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:272` / `_valid_materials` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:318` / `prepare_group` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:319` / `prepare_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:322` / `prepare_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:374` / `prepare_group` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/unified_checkout.py:417` / `payment_scopes` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/unified_checkout.py:424` / `payment_scopes` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:442` / `payment_scope` | S | query/ORM | `payment_scopes(db, {communication.payment_group_id}, tenant_id=communication.tenant_id).get` | ver matriz |
| `backend/app/unified_checkout.py:446` / `lock_payment_scope` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:449` / `lock_payment_scope` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:482` / `report_group` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:483` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:484` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:491` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:541` / `report_group` | S | produtor | `PaymentCommunication` | ver matriz |
| `backend/app/unified_checkout.py:547` / `report_group` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/unified_checkout.py:558` / `finalize_selection` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:559` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:560` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:564` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:585` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:599` / `finalize_selection` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/unified_checkout.py:603` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:85` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:94` / `_materials` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:107` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:117` / `_materials` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:152` / `cart_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:188` / `cart_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:344` / `prepare_group` | S | produtor | `PaymentGroup` | ver matriz |
| `backend/app/unified_checkout.py:359` / `prepare_group` | S | query/ORM | `drafts.get` | ver matriz |
| `backend/app/unified_checkout.py:411` / `group_payload` | S | query/ORM | `group.pix_configuration_snapshot.get` | ver matriz |
| `backend/app/unified_checkout.py:456` / `lock_payment_scope` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:463` / `lock_payment_scope` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:504` / `report_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:537` / `report_group` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:594` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:595` / `finalize_selection` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/unified_checkout.py:176` / `cart_payload` | S | query/ORM | `folders.get` | ver matriz |
| `backend/app/unified_checkout.py:329` / `prepare_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:382` / `prepare_group` | S | query/ORM | `drafts.get` | ver matriz |
| `backend/app/unified_checkout.py:382` / `prepare_group` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/unified_checkout.py:422` / `payment_scopes` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:525` / `report_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:598` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:226` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:569` / `finalize_selection` | S | query/ORM | `(existing.price_rule_snapshot or {}).get` | ver matriz |
| `backend/app/unified_checkout.py:597` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:165` / `cart_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:60` / `communications_for_orders` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:422` / `payment_scopes` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:425` / `payment_scopes` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:449` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:492` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:564` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:603` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:86` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:108` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:153` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:189` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:457` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:538` / `report_group` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:594` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:113` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:232` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:319` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:323` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:330` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:483` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:485` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:526` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:559` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:585` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:598` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:597` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:166` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:560` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:464` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:505` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:562` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/web_push.py:30` / `push_configuration_ready` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:31` / `push_configuration_ready` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:32` / `push_configuration_ready` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:134` / `send_push` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:135` / `send_push` | N | query/ORM | `os.environ.get` | ver matriz |
| `backend/app/web_push.py:143` / `send_push` | N | efeito potencial | `payload['id'].replace` | ver matriz |
| `backend/app/whatsapp_binding.py:73` / `resolve_binding` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/whatsapp_binding.py:75` / `resolve_binding` | N | query/ORM | `aliases.get` | ver matriz |
| `backend/app/whatsapp_binding.py:163` / `provider_for` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:173` / `photographer_phone` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:174` / `photographer_phone` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_binding.py:185` / `webhook_owner` | N | query/ORM | `payload.get` | ver matriz |
| `backend/app/whatsapp_binding.py:142` / `send_transactional` | N | efeito potencial | `self.adapter.send_transactional` | ver matriz |
| `backend/app/whatsapp_binding.py:199` / `webhook_owner` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:137` / `validate` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_binding.py:78` / `resolve_binding` | N | gate | `require_single_tenant` | ver matriz |
| `backend/app/whatsapp_binding.py:193` / `webhook_owner` | N | gate | `require_single_tenant` | ver matriz |
| `backend/app/whatsapp_binding.py:174` / `photographer_phone` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_channel.py:53` / `channel_settings` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/whatsapp_channel.py:55` / `channel_settings` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/whatsapp_channel.py:66` / `channel_settings` | N | produtor | `WhatsAppChannelSettings` | ver matriz |
| `backend/app/whatsapp_channel.py:72` / `channel_settings` | N | query/ORM | `db.add` | ver matriz |
| `backend/app/whatsapp_channel.py:171` / `channel_payload` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_channel.py:56` / `channel_settings` | N | query/ORM | `select` | ver matriz |
| `backend/app/whatsapp_channel.py:63` / `channel_settings` | N | gate | `resolve_binding` | ver matriz |
| `backend/app/whatsapp_delivery.py:59` / `encrypt_otp` | N | efeito potencial | `AESGCM(key).encrypt` | ver matriz |
| `backend/app/whatsapp_delivery.py:66` / `decrypt_otp` | N | efeito potencial | `AESGCM(key).decrypt(raw[:12], raw[12:], context.encode('utf-8')).decode` | ver matriz |
| `backend/app/whatsapp_delivery.py:66` / `decrypt_otp` | N | efeito potencial | `AESGCM(key).decrypt` | ver matriz |
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
| `backend/app/worker.py:105` / `payment_notification_message` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:106` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:140` / `materialize_payment_delivery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:141` / `materialize_payment_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:146` / `materialize_payment_delivery` | X | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/worker.py:159` / `materialize_payment_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:171` / `mirror_payment_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:228` / `delivery_message` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:257` / `_record_attempt` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:765` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:107` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:108` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:109` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:110` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:193` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:242` / `delivery_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:258` / `_record_attempt` | X | produtor | `WhatsAppDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:288` / `process_next_media_job` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:310` / `process_next_media_job` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:311` / `process_next_media_job` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:389` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:412` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:427` / `process_next_whatsapp_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:446` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:532` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:533` / `validate_email_origin` | X | query/ORM | `{'password_recovery': 'password_reset', 'email_verification': 'verify_admin_email'}.get` | ver matriz |
| `backend/app/worker.py:561` / `process_next_email_delivery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:579` / `process_next_email_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:589` / `process_next_email_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:605` / `process_next_email_delivery` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:690` / `materialize_next_payment_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:703` / `materialize_next_payment_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:768` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:770` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:779` / `process_next_gallery_reopening_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:814` / `reconcile_next_unknown_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:826` / `reconcile_next_unknown_delivery` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:849` / `run_cycle` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:894` / `process_asset_file_cleanup` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:956` / `process_admin_security_cleanup` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:198` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:202` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:206` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:276` / `process_next_media_job` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:459` / `process_next_whatsapp_delivery` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:462` / `process_next_whatsapp_delivery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:463` / `process_next_whatsapp_delivery` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:534` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:619` / `process_next_email_delivery` | X | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/worker.py:625` / `process_next_email_delivery` | X | efeito potencial | `active_provider.send` | ver matriz |
| `backend/app/worker.py:637` / `process_next_email_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:739` / `send` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:747` / `send` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:753` / `send` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:766` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:790` / `process_next_gallery_reopening_notification` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:796` / `process_next_gallery_reopening_notification` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:934` / `process_otp_privacy_cleanup` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:959` / `process_admin_security_cleanup` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:142` / `materialize_payment_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:171` / `mirror_payment_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:212` / `validate_otp_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:218` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:235` / `delivery_message` | X | efeito potencial | `decrypt_otp` | ver matriz |
| `backend/app/worker.py:324` / `process_next_media_job` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:330` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:332` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:334` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:488` / `process_next_whatsapp_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:542` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:638` / `process_next_email_delivery` | X | produtor | `EmailDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:676` / `process_next_email_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:962` / `process_admin_security_cleanup` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:446` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:562` / `process_next_email_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:677` / `process_next_email_delivery` | X | produtor | `EmailDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:704` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:235` / `delivery_message` | X | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/worker.py:934` / `process_otp_privacy_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:959` / `process_admin_security_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:213` / `validate_otp_origin` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/worker.py:325` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:390` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:428` / `process_next_whatsapp_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:488` / `process_next_whatsapp_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:548` / `validate_email_origin` | X | query/ORM | `payload.get` | ver matriz |
| `backend/app/worker.py:590` / `process_next_email_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:580` / `process_next_email_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:413` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:691` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:779` / `process_next_gallery_reopening_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:815` / `reconcile_next_unknown_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:276` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:292` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:693` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:894` / `process_asset_file_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:289` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `scripts/assert_homolog_schema_head.py:30` / `migration_heads` | T | query/ORM | `values.get` | ver matriz |
| `scripts/assert_homolog_schema_head.py:35` / `migration_heads` | T | query/ORM | `values.get` | ver matriz |
| `scripts/embedding_engine_benchmark.py:23` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/embedding_engine_benchmark.py:24` / `<módulo>` | T | query/ORM | `sys.path.insert` | ver matriz |
| `scripts/embedding_engine_benchmark.py:76` / `load_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/embedding_engine_benchmark.py:66` / `load_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/embedding_engine_benchmark.py:288` / `main` | T | efeito potencial | `args.output.open` | ver matriz |
| `scripts/embedding_engine_benchmark.py:63` / `load_manifest` | T | query/ORM | `manifest.get` | ver matriz |
| `scripts/embedding_engine_benchmark.py:69` / `load_manifest` | T | query/ORM | `auth.get` | ver matriz |
| `scripts/embedding_engine_benchmark.py:83` / `load_manifest` | T | query/ORM | `item.get` | ver matriz |
| `scripts/embedding_engine_benchmark.py:218` / `benchmark` | T | efeito potencial | `Image.open` | ver matriz |
| `scripts/embedding_engine_benchmark.py:67` / `load_manifest` | T | query/ORM | `auth.get` | ver matriz |
| `scripts/embedding_engine_benchmark.py:90` / `load_manifest` | T | query/ORM | `face.get` | ver matriz |
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
| `scripts/preview_adjustment_smoke.py:47` / `<módulo>` | T | query/ORM | `draw.text` | ver matriz |
| `scripts/preview_adjustment_smoke.py:48` / `<módulo>` | T | query/ORM | `draw.text` | ver matriz |

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
| `backend/app/facial/face_worker.py:10` | F | armazenamento/cache/wake-up |
| `backend/app/facial/face_worker.py:175` | F | armazenamento/cache/wake-up |
| `backend/app/facial/face_worker.py:176` | F | armazenamento/cache/wake-up |
| `backend/app/facial/gemma_assets.py:44` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:1` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:60` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:362` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:375` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:109` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:111` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:134` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:136` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:159` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:22` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:70` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:75` | F | armazenamento/cache/wake-up |
| `backend/app/installation_operator.py:13` | O | armazenamento/cache/wake-up |
| `backend/app/main.py:434` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1077` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1333` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2629` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2773` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2778` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2848` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2858` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2859` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2939` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2954` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6431` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6473` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6541` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6565` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:9677` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:11607` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:21` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:30` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:31` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:34` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:36` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:37` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:38` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:75` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:77` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:79` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:80` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:82` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:83` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:84` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:86` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:96` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:97` | X | armazenamento/cache/wake-up |
| `backend/app/storage_metrics.py:102` | X | armazenamento/cache/wake-up |
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
| `scripts/deploy-homolog.sh:607` | T | armazenamento/cache/wake-up |
| `scripts/deploy-homolog.sh:609` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:28` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:47` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:49` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:88` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:91` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:113` | T | armazenamento/cache/wake-up |
| `scripts/face_spike/models.py:116` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:76` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:92` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:119` | T | armazenamento/cache/wake-up |
| `scripts/maintain-homolog-data.sh:170` | T | armazenamento/cache/wake-up |
| `scripts/resume-homolog.sh:163` | T | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:45` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:78` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:128` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:137` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-report.ts:57` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-report.ts:117` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:76` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:311` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:336` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:26` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:47` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:210` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:218` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:15` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:24` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:38` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:140` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:170` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:99` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:326` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:339` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:812` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:854` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/installation-diagnostics.tsx:27` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/notifications/page.tsx:64` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/facial-engine-panel.tsx:27` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/infinitepay-panel.tsx:15` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/page.tsx:331` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:77` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:126` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:219` | U | armazenamento/cache/wake-up |
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
| `frontend/app/admin-session-toolbar.tsx:18` | U | armazenamento/cache/wake-up |
| `frontend/app/auth-entry.tsx:79` | U | armazenamento/cache/wake-up |
| `frontend/app/authenticated-identity.tsx:16` | U | armazenamento/cache/wake-up |
| `frontend/app/client-navigation.tsx:18` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-client.ts:89` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:7` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:9` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:20` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:26` | U | armazenamento/cache/wake-up |
| `frontend/app/facial-search-storage.ts:27` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:88` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:115` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:126` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:153` | U | armazenamento/cache/wake-up |
| `frontend/app/gallery-presentation.tsx:158` | U | armazenamento/cache/wake-up |
| `frontend/app/install-app.tsx:45` | U | armazenamento/cache/wake-up |
| `frontend/app/library/cart/page.tsx:39` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:53` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:81` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:87` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:88` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:89` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchases/page.tsx:32` | U | armazenamento/cache/wake-up |
| `frontend/app/monitor-activity.tsx:17` | U | armazenamento/cache/wake-up |
| `frontend/app/monitor-activity.tsx:25` | U | armazenamento/cache/wake-up |
| `frontend/app/public-galleries/[galleryId]/page.tsx:81` | U | armazenamento/cache/wake-up |
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
| `frontend/app/upload-jpeg.ts:19` | U | armazenamento/cache/wake-up |
| `frontend/public/markina-sw.js:1` | U | armazenamento/cache/wake-up |
| `frontend/public/markina-sw.js:53` | U | armazenamento/cache/wake-up |
