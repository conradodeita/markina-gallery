# Inventário de código — complemento da matriz

Gerado por `inventory_ownership.py`; consultar `ownership-matrix.md` para decisões, critérios A–X, testes e limites. Este inventário estático associa fontes a critérios; não executa testes nem decide prontidão. O estado e as evidências de implementação/validação estão na matriz e em `validation.md`.

SHA256 das fontes inventariadas: `36d610205259a3b3a299c20e35a1d4b966087d06a9255d0f3e59ae620e8b64d0`.

Contagens: arquivos=205; efeito potencial=210; estado=144; gate=671; produtor=135; query/ORM=2335; rotas=243; sitios=3350; tabelas=79.

## Tabelas

| Tabela/modelo | Classe | Critério/teste | Fonte | FKs atuais | Evidência por critério |
| --- | --- | --- | --- | --- | --- |
| `branding_settings` / `BrandingSettings` | R | K | `backend/app/auth.py:99` | tenant.id | ver matriz |
| `admin_user` / `AdminUser` | I | A | `backend/app/auth.py:142` | sem FK | ver matriz |
| `installation_operator` / `InstallationOperator` | I | O | `backend/app/auth.py:152` | admin_user.id | ver matriz |
| `tenant` / `Tenant` | I | A | `backend/app/auth.py:167` | sem FK | ver matriz |
| `tenant_admin` / `TenantAdmin` | D | A | `backend/app/auth.py:177` | admin_user.id; tenant.id | ver matriz |
| `admin_security_challenge` / `AdminSecurityChallenge` | M | A | `backend/app/auth.py:187` | admin_user.id; tenant.id | ver matriz |
| `admin_action_token` / `AdminActionToken` | I | A | `backend/app/auth.py:219` | admin_user.id | ver matriz |
| `email_delivery` / `EmailDelivery` | I | A | `backend/app/auth.py:235` | sem FK | ver matriz |
| `email_delivery_attempt` / `EmailDeliveryAttempt` | I | A | `backend/app/auth.py:268` | email_delivery.id | ver matriz |
| `client` / `Client` | R | C | `backend/app/auth.py:285` | tenant.id | ver matriz |
| `client_phone` / `ClientPhone` | D | C | `backend/app/auth.py:297` | client.id; tenant.id; composta:fk_client_phone_client_tenant | ver matriz |
| `client_deletion_receipt` / `ClientDeletionReceipt` | R | C | `backend/app/auth.py:335` | admin_user.id; tenant.id | ver matriz |
| `gallery_access` / `GalleryAccess` | R | G | `backend/app/auth.py:370` | client.id; derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `parent_gallery` / `ParentGallery` | R | G | `backend/app/auth.py:396` | photo_asset.id; progressive_pricing_preset.id; tenant.id | ver matriz |
| `parent_gallery_registration` / `ParentGalleryRegistration` | D | G | `backend/app/auth.py:467` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `photo_asset` / `PhotoAsset` | R | G | `backend/app/auth.py:483` | derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_photo_asset_folder_gallery; composta:fk_photo_asset_folder_scope; composta:fk_photo_asset_parent_tenant; composta:fk_photo_asset_private_tenant | ver matriz |
| `photo_folder` / `PhotoFolder` | D | G | `backend/app/auth.py:529` | derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `gallery_client_state` / `GalleryClientState` | D | G | `backend/app/auth.py:593` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `folder_client_grant` / `FolderClientGrant` | D | G | `backend/app/auth.py:619` | tenant.id; composta:fk_folder_client_grant_client_state; composta:fk_folder_client_grant_folder_parent | ver matriz |
| `derived_gallery` / `DerivedGallery` | R | G | `backend/app/auth.py:649` | client.id; parent_gallery.id; tenant.id; composta:fk_derived_gallery_parent_tenant | ver matriz |
| `derived_gallery_membership` / `DerivedGalleryMembership` | D | G | `backend/app/auth.py:687` | admin_user.id; client.id; parent_gallery.id; tenant.id; composta:fk_membership_gallery_parent | ver matriz |
| `derived_gallery_photo` / `DerivedGalleryPhoto` | D | G | `backend/app/auth.py:740` | derived_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `derived_gallery_photo_origin` / `DerivedGalleryPhotoOrigin` | D | G | `backend/app/auth.py:766` | derived_gallery_photo.id; tenant.id | ver matriz |
| `photo_selection` / `PhotoSelection` | D | S | `backend/app/auth.py:794` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_favorite` / `PhotoFavorite` | D | S | `backend/app/auth.py:828` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_view` / `PhotoView` | D | S | `backend/app/auth.py:861` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `photo_comment` / `PhotoComment` | D | S | `backend/app/auth.py:894` | client.id; derived_gallery.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `payment_group` / `PaymentGroup` | R | S | `backend/app/auth.py:921` | client.id; tenant.id | ver matriz |
| `sale_order` / `SaleOrder` | R | S | `backend/app/auth.py:949` | client.id; derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_sale_order_canonical_state; composta:fk_sale_order_payment_group_owner | ver matriz |
| `sale_order_item` / `SaleOrderItem` | D | S | `backend/app/auth.py:1052` | photo_asset.id; sale_order.id; tenant.id | ver matriz |
| `removed_photo_movement` / `RemovedPhotoMovement` | R | S | `backend/app/auth.py:1075` | client.id; tenant.id | ver matriz |
| `asset_file_cleanup` / `AssetFileCleanup` | R | L | `backend/app/auth.py:1098` | tenant.id | ver matriz |
| `gallery_lifecycle_operation` / `GalleryLifecycleOperation` | R | L | `backend/app/auth.py:1114` | tenant.id | ver matriz |
| `gallery_access_capability` / `GalleryAccessCapability` | D | G | `backend/app/auth.py:1167` | client.id; derived_gallery.id; gallery_access_capability.id; parent_gallery.id; tenant.id | ver matriz |
| `commercial_history_media` / `CommercialHistoryMedia` | R | S | `backend/app/auth.py:1262` | sale_order_item.id; tenant.id | ver matriz |
| `price_rule` / `PriceRule` | D | K | `backend/app/auth.py:1372` | parent_gallery.id; tenant.id | ver matriz |
| `pix_checkout_settings` / `PixCheckoutSettings` | D | K | `backend/app/auth.py:1393` | parent_gallery.id; tenant.id | ver matriz |
| `global_pix_settings` / `GlobalPixSettings` | R | K | `backend/app/auth.py:1419` | admin_user.id; tenant.id | ver matriz |
| `payment_communication` / `PaymentCommunication` | D | S | `backend/app/auth.py:1448` | admin_user.id; client.id; sale_order.id; tenant.id; composta:fk_payment_communication_group_owner | ver matriz |
| `payment_confirmation_correction` / `PaymentConfirmationCorrection` | D | S | `backend/app/auth.py:1473` | admin_user.id; payment_communication.id; sale_order.id; tenant.id | ver matriz |
| `payment_message_template` / `PaymentMessageTemplate` | R | K | `backend/app/auth.py:1509` | tenant.id | ver matriz |
| `payment_notification_outbox` / `PaymentNotificationOutbox` | D | N | `backend/app/auth.py:1521` | payment_communication.id; tenant.id | ver matriz |
| `gallery_reopening_request` / `GalleryReopeningRequest` | D | S | `backend/app/auth.py:1547` | admin_user.id; client.id; derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_gallery_reopening_canonical_state | ver matriz |
| `gallery_reopening_notification_outbox` / `GalleryReopeningNotificationOutbox` | D | N | `backend/app/auth.py:1620` | gallery_reopening_request.id; tenant.id | ver matriz |
| `progressive_pricing_preset` / `ProgressivePricingPreset` | R | K | `backend/app/auth.py:1652` | tenant.id | ver matriz |
| `progressive_pricing_tier` / `ProgressivePricingTier` | D | K | `backend/app/auth.py:1673` | progressive_pricing_preset.id; tenant.id | ver matriz |
| `gallery_membership_notification_outbox` / `GalleryMembershipNotificationOutbox` | R | N | `backend/app/auth.py:1702` | client.id; derived_gallery.id; parent_gallery.id; tenant.id | ver matriz |
| `whatsapp_channel_settings` / `WhatsAppChannelSettings` | R | K | `backend/app/auth.py:1768` | tenant.id | ver matriz |
| `whatsapp_delivery` / `WhatsAppDelivery` | R | N | `backend/app/auth.py:1792` | tenant.id | ver matriz |
| `whatsapp_delivery_attempt` / `WhatsAppDeliveryAttempt` | D | N | `backend/app/auth.py:1836` | tenant.id; whatsapp_delivery.id | ver matriz |
| `whatsapp_webhook_receipt` / `WhatsAppWebhookReceipt` | R | N | `backend/app/auth.py:1856` | tenant.id | ver matriz |
| `media_derivative` / `MediaDerivative` | D | P | `backend/app/auth.py:1869` | photo_asset.id; tenant.id | ver matriz |
| `media_job` / `MediaJob` | R | P | `backend/app/auth.py:1893` | photo_asset.id; tenant.id | ver matriz |
| `preview_adjustment_settings` / `PreviewAdjustmentSettings` | R | K | `backend/app/auth.py:1917` | tenant.id | ver matriz |
| `gallery_preview_settings` / `GalleryPreviewSettings` | D | K | `backend/app/auth.py:1936` | parent_gallery.id; tenant.id | ver matriz |
| `folder_processing_settings` / `FolderProcessingSettings` | D | K | `backend/app/auth.py:1958` | photo_folder.id; tenant.id | ver matriz |
| `preview_adjustment` / `PreviewAdjustment` | D | P | `backend/app/auth.py:1983` | photo_asset.id; tenant.id | ver matriz |
| `gallery_facial_policy` / `GalleryFacialPolicy` | D | F | `backend/app/auth.py:2009` | admin_user.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_rollout` / `FacialRollout` | D | F | `backend/app/auth.py:2054` | admin_user.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_calibration_approval` / `FacialCalibrationApproval` | R | F | `backend/app/auth.py:2123` | admin_user.id; tenant.id | ver matriz |
| `facial_rollout_operation` / `FacialRolloutOperation` | R | F | `backend/app/auth.py:2182` | admin_user.id; tenant.id | ver matriz |
| `facial_legal_representation` / `FacialLegalRepresentation` | D | F | `backend/app/auth.py:2226` | admin_user.id; client.id; parent_gallery.id; tenant.id | ver matriz |
| `photo_analysis` / `PhotoAnalysis` | D | F | `backend/app/auth.py:2285` | photo_asset.id; tenant.id | ver matriz |
| `photo_face_embedding` / `PhotoFaceEmbedding` | D | F | `backend/app/auth.py:2314` | derived_gallery.id; parent_gallery.id; tenant.id; composta:fk_face_embedding_photo_parent | ver matriz |
| `facial_search_request` / `FacialSearchRequest` | R | F | `backend/app/auth.py:2393` | client.id; gallery_facial_policy.id; parent_gallery.id; tenant.id | ver matriz |
| `facial_search_snapshot_item` / `FacialSearchSnapshotItem` | D | F | `backend/app/auth.py:2473` | tenant.id; composta:fk_facial_snapshot_photo_parent; composta:fk_facial_snapshot_search_scope | ver matriz |
| `facial_search_candidate` / `FacialSearchCandidate` | D | F | `backend/app/auth.py:2520` | tenant.id; composta:fk_facial_candidate_photo_parent; composta:fk_facial_candidate_search_scope | ver matriz |
| `facial_job` / `FacialJob` | R | F | `backend/app/auth.py:2565` | derived_gallery.id; facial_search_request.id; parent_gallery.id; photo_asset.id; tenant.id | ver matriz |
| `facial_search_notification_outbox` / `FacialSearchNotificationOutbox` | D | F | `backend/app/auth.py:2625` | tenant.id; composta:fk_facial_notification_search_scope | ver matriz |
| `auth_challenge` / `AuthChallenge` | M | A | `backend/app/auth.py:2680` | tenant.id | ver matriz |
| `notification_setting` / `NotificationSetting` | R | K | `backend/app/auth.py:2704` | tenant.id | ver matriz |
| `notification_milestone` / `NotificationMilestone` | D | N | `backend/app/auth.py:2722` | client.id; parent_gallery.id; tenant.id | ver matriz |
| `push_subscription` / `PushSubscription` | R | N | `backend/app/auth.py:2740` | admin_user.id; auth_session.id; client.id; tenant.id | ver matriz |
| `notification_event` / `NotificationEvent` | R | N | `backend/app/auth.py:2775` | client.id; derived_gallery.id; parent_gallery.id; sale_order.id; tenant.id | ver matriz |
| `notification_delivery` / `NotificationDelivery` | D | N | `backend/app/auth.py:2804` | admin_user.id; client.id; notification_event.id; push_subscription.id; tenant.id | ver matriz |
| `private_upload_batch` / `PrivateUploadBatch` | D | G | `backend/app/auth.py:2849` | admin_user.id; derived_gallery.id; tenant.id | ver matriz |
| `private_upload_batch_asset` / `PrivateUploadBatchAsset` | D | G | `backend/app/auth.py:2867` | photo_asset.id; private_upload_batch.id; tenant.id | ver matriz |
| `auth_session` / `AuthSession` | M | A | `backend/app/auth.py:2880` | admin_user.id; client.id; tenant.id | ver matriz |
| `audit_event` / `AuditEvent` | M | A | `backend/app/auth.py:2906` | tenant.id | ver matriz |

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
| `backend/app/facial/status.py` | F | ver matriz |
| `backend/app/facial/worker.py` | F | ver matriz |
| `backend/app/folder_processing.py` | P | ver matriz |
| `backend/app/folder_processing_api.py` | P | ver matriz |
| `backend/app/gallery_access.py` | G | ver matriz |
| `backend/app/gallery_cleanup.py` | L | ver matriz |
| `backend/app/gallery_lifecycle.py` | L | ver matriz |
| `backend/app/gallery_pricing.py` | K | ver matriz |
| `backend/app/gallery_visuals.py` | G | ver matriz |
| `backend/app/global_pix.py` | K | ver matriz |
| `backend/app/historical_media.py` | X | ver matriz |
| `backend/app/homolog_cleanup.py` | L | ver matriz |
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
| `backend/app/provision_installation_operator.py` | O | ver matriz |
| `backend/app/provision_photographer.py` | A | ver matriz |
| `backend/app/public_gallery_access.py` | G | ver matriz |
| `backend/app/public_origin.py` | I | ver matriz |
| `backend/app/push_subscriptions.py` | N | ver matriz |
| `backend/app/seed_admin.py` | A | ver matriz |
| `backend/app/storage_metrics.py` | X | ver matriz |
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
| `scripts/deploy-homolog.sh` | T | ver matriz |
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
| `frontend/app/admin/settings/page.tsx` | U | ver matriz |
| `frontend/app/admin/settings/pix-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/security-panel.tsx` | U | ver matriz |
| `frontend/app/admin/settings/whatsapp-panel.tsx` | U | ver matriz |
| `frontend/app/admin/statistics/page.tsx` | U | ver matriz |
| `frontend/app/api/health/route.ts` | U | ver matriz |
| `frontend/app/auth-entry.tsx` | U | ver matriz |
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
| `PATCH /admin/photo-folders/{folder_id}/processing` | R/P | `backend/app/folder_processing_api.py:95` / `save` | sem Depends na assinatura | ver matriz |
| `POST /admin/photo-folders/{folder_id}/processing/preview/enqueue` | R/P | `backend/app/folder_processing_api.py:112` / `enqueue_folder_preview` | sem Depends na assinatura | ver matriz |
| `POST /admin/photo-folders/{folder_id}/processing/facial/reprocess` | R/F | `backend/app/folder_processing_api.py:132` / `reprocess_folder_facial` | sem Depends na assinatura | ver matriz |
| `GET /health` | I/I | `backend/app/main.py:1226` / `health` | sem Depends na assinatura | ver matriz |
| `POST /internal/whatsapp/webhook` | R/N | `backend/app/main.py:1231` / `whatsapp_webhook` | db_session | ver matriz |
| `GET /admin/whatsapp/channel` | R/N | `backend/app/main.py:1268` / `admin_whatsapp_channel` | db_session | ver matriz |
| `PATCH /admin/whatsapp/channel` | R/N | `backend/app/main.py:1283` / `update_admin_whatsapp_channel` | db_session | ver matriz |
| `POST /admin/whatsapp/channel/refresh` | R/N | `backend/app/main.py:1297` / `refresh_admin_whatsapp_channel` | db_session | ver matriz |
| `POST /admin/whatsapp/channel/pairing` | R/N | `backend/app/main.py:1307` / `pair_admin_whatsapp_channel` | db_session | ver matriz |
| `GET /admin/whatsapp/deliveries` | R/N | `backend/app/main.py:1330` / `admin_whatsapp_deliveries` | db_session | ver matriz |
| `POST /admin/whatsapp/deliveries/{delivery_id}/retry` | R/N | `backend/app/main.py:1356` / `retry_admin_whatsapp_delivery` | db_session | ver matriz |
| `POST /auth/client/challenge` | M/A | `backend/app/main.py:1470` / `client_challenge` | db_session | ver matriz |
| `POST /auth/client/resend` | M/A | `backend/app/main.py:1505` / `client_resend` | db_session | ver matriz |
| `POST /auth/client/verify` | M/A | `backend/app/main.py:1517` / `client_verify` | db_session | ver matriz |
| `POST /auth/admin/password` | M/A | `backend/app/main.py:1787` / `admin_password` | db_session | ver matriz |
| `POST /auth/admin/totp` | M/A | `backend/app/main.py:1816` / `admin_totp` | db_session | ver matriz |
| `POST /auth/admin/recovery/challenge` | M/A | `backend/app/main.py:1854` / `admin_recovery_challenge` | db_session | ver matriz |
| `POST /auth/admin/recovery/resend` | M/A | `backend/app/main.py:1895` / `admin_recovery_resend` | db_session | ver matriz |
| `POST /auth/admin/recovery/verify` | M/A | `backend/app/main.py:1918` / `admin_recovery_verify` | db_session | ver matriz |
| `POST /auth/admin/recovery/reset` | M/A | `backend/app/main.py:1943` / `admin_recovery_reset` | db_session | ver matriz |
| `POST /auth/admin/email/confirm` | M/A | `backend/app/main.py:1977` / `confirm_admin_email` | db_session | ver matriz |
| `GET /auth/destination` | M/A | `backend/app/main.py:2025` / `destination` | sem Depends na assinatura | ver matriz |
| `POST /auth/logout` | M/A | `backend/app/main.py:2035` / `logout` | sem Depends na assinatura | ver matriz |
| `POST /auth/revoke-all` | M/A | `backend/app/main.py:2055` / `revoke_all` | sem Depends na assinatura | ver matriz |
| `GET /admin` | M/A | `backend/app/main.py:2066` / `admin_area` | sem Depends na assinatura | ver matriz |
| `GET /admin/email/channel` | M/A | `backend/app/main.py:2072` / `admin_email_channel` | db_session | ver matriz |
| `GET /admin/security/summary` | M/A | `backend/app/main.py:2093` / `admin_security_summary` | db_session | ver matriz |
| `GET /admin/settings/pix` | R/K | `backend/app/main.py:2110` / `admin_global_pix` | db_session | ver matriz |
| `POST /admin/settings/pix/challenge` | R/K | `backend/app/main.py:2117` / `admin_global_pix_challenge` | db_session | ver matriz |
| `POST /admin/settings/pix/confirm` | R/K | `backend/app/main.py:2163` / `admin_global_pix_confirm` | db_session | ver matriz |
| `POST /admin/security/password/challenge` | M/A | `backend/app/main.py:2196` / `admin_password_change_challenge` | db_session | ver matriz |
| `POST /admin/security/password/confirm` | M/A | `backend/app/main.py:2229` / `admin_password_change_confirm` | db_session | ver matriz |
| `POST /admin/security/email/challenge` | M/A | `backend/app/main.py:2262` / `admin_email_change_challenge` | db_session | ver matriz |
| `POST /admin/security/email/verify-otp` | M/A | `backend/app/main.py:2301` / `admin_email_change_verify_otp` | db_session | ver matriz |
| `GET /branding` | M/K | `backend/app/main.py:2359` / `public_branding` | db_session | ver matriz |
| `GET /admin/branding` | M/K | `backend/app/main.py:2371` / `admin_branding` | db_session | ver matriz |
| `PATCH /admin/branding` | M/K | `backend/app/main.py:2381` / `update_admin_branding` | db_session | ver matriz |
| `PATCH /admin/branding/protection` | M/K | `backend/app/main.py:2395` / `update_visual_protection` | db_session | ver matriz |
| `PUT /admin/branding/{asset}` | M/K | `backend/app/main.py:2422` / `upload_branding_asset` | db_session | ver matriz |
| `GET /branding/{asset}` | M/K | `backend/app/main.py:2451` / `public_branding_asset` | db_session | ver matriz |
| `GET /admin/validation-summary` | R/L | `backend/app/main.py:2516` / `admin_validation_summary` | db_session | ver matriz |
| `GET /admin/installation-capabilities` | I/O | `backend/app/main.py:2577` / `admin_installation_capabilities` | sem Depends na assinatura | ver matriz |
| `GET /admin/capacity-observability` | I/O | `backend/app/main.py:2587` / `admin_capacity_observability` | sem Depends na assinatura | ver matriz |
| `GET /admin/facial-observability` | I/O | `backend/app/main.py:2600` / `admin_facial_observability` | db_session | ver matriz |
| `GET /admin/clients` | R/C | `backend/app/main.py:2628` / `admin_clients` | db_session | ver matriz |
| `POST /admin/clients` | R/C | `backend/app/main.py:2643` / `create_client` | db_session | ver matriz |
| `PATCH /admin/clients/{client_id}` | R/C | `backend/app/main.py:2674` / `update_client_name` | db_session | ver matriz |
| `GET /admin/clients/{client_id}/deletion-inventory` | R/L | `backend/app/main.py:2691` / `get_client_deletion_inventory` | db_session | ver matriz |
| `DELETE /admin/clients/{client_id}` | R/L | `backend/app/main.py:2703` / `delete_client` | db_session | ver matriz |
| `GET /admin/parent-galleries` | R/G | `backend/app/main.py:2828` / `admin_parent_galleries` | db_session | ver matriz |
| `GET /admin/parent-galleries/overview` | R/G | `backend/app/main.py:2847` / `parent_gallery_overview` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/editor` | R/G | `backend/app/main.py:3049` / `parent_gallery_editor` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/settings` | R/G | `backend/app/main.py:3152` / `parent_gallery_settings` | db_session | ver matriz |
| `PATCH /admin/parent-galleries/{parent_gallery_id}/settings` | R/G | `backend/app/main.py:3179` / `update_parent_gallery_settings` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/summary` | R/G | `backend/app/main.py:3196` / `parent_gallery_summary` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/cover` | R/G | `backend/app/main.py:3254` / `set_parent_gallery_cover` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/cover` | R/G | `backend/app/main.py:3291` / `clear_parent_gallery_cover` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/sales` | R/S | `backend/app/main.py:3304` / `parent_gallery_sales` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/sales` | R/S | `backend/app/main.py:3329` / `update_parent_gallery_sales` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/details` | R/G | `backend/app/main.py:3356` / `parent_gallery_details` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/cover-photos` | R/G | `backend/app/main.py:3415` / `register_parent_gallery_cover_photo` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-policy` | R/F | `backend/app/main.py:3460` / `admin_parent_gallery_facial_policy` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/facial-policy` | R/F | `backend/app/main.py:3478` / `prepare_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/activate` | R/F | `backend/app/main.py:3510` / `activate_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/suspend` | R/F | `backend/app/main.py:3549` / `suspend_parent_gallery_facial_policy` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-policy/revoke` | R/F | `backend/app/main.py:3574` / `revoke_parent_gallery_facial_policy` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-cleanup-proof` | R/F | `backend/app/main.py:3599` / `admin_parent_gallery_facial_cleanup_proof` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/facial-index` | R/F | `backend/app/main.py:3611` / `admin_parent_gallery_facial_index` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/facial-index` | R/F | `backend/app/main.py:3684` / `admin_private_gallery_facial_index` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-index/retry` | R/F | `backend/app/main.py:3755` / `retry_parent_gallery_facial_index` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/facial-index/reprocess` | R/F | `backend/app/main.py:3795` / `reprocess_parent_gallery_facial_index` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:3850` / `admin_parent_gallery_photos` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/available-photos` | R/G | `backend/app/main.py:3873` / `admin_parent_gallery_available_photos` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/folders` | R/G | `backend/app/main.py:3943` / `admin_parent_gallery_folders` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/folders` | R/G | `backend/app/main.py:4028` / `create_photo_folder` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders` | R/G | `backend/app/main.py:4076` / `admin_client_restricted_folders` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders` | R/G | `backend/app/main.py:4129` / `create_admin_client_restricted_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}` | R/G | `backend/app/main.py:4185` / `grant_restricted_folder_client` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}` | R/L | `backend/app/main.py:4250` / `revoke_restricted_folder_client` | db_session | ver matriz |
| `PATCH /admin/photo-folders/{folder_id}` | R/G | `backend/app/main.py:4291` / `rename_photo_folder` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}` | R/L | `backend/app/main.py:4318` / `delete_photo_folder` | db_session | ver matriz |
| `GET /admin/photo-folders/{folder_id}/photos` | R/G | `backend/app/main.py:4353` / `admin_photo_folder_photos` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}/photos/{photo_id}` | R/L | `backend/app/main.py:4400` / `delete_folder_photo_asset` | db_session | ver matriz |
| `DELETE /admin/photo-folders/{folder_id}/photos` | R/L | `backend/app/main.py:4492` / `delete_folder_photo_assets` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/photos` | R/G | `backend/app/main.py:4525` / `register_folder_photo_asset` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/publish` | R/G | `backend/app/main.py:4653` / `publish_photo_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/publish-ready` | R/G | `backend/app/main.py:4677` / `publish_parent_gallery_ready_photos` | db_session | ver matriz |
| `POST /admin/photo-folders/{folder_id}/release` | R/G | `backend/app/main.py:4709` / `release_photo_folder` | db_session | ver matriz |
| `POST /admin/parent-galleries` | R/G | `backend/app/main.py:4741` / `create_parent_gallery` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:4790` / `parent_gallery_public_link_status` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:4819` / `issue_parent_gallery_public_link` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/public-link/rotate` | R/G | `backend/app/main.py:4849` / `rotate_parent_gallery_public_link` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/public-link` | R/G | `backend/app/main.py:4883` / `revoke_parent_gallery_public_link` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite` | R/G | `backend/app/main.py:4934` / `issue_parent_gallery_client_invite` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite/rotate` | R/G | `backend/app/main.py:4961` / `rotate_parent_gallery_client_invite` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite` | R/L | `backend/app/main.py:4996` / `revoke_parent_gallery_client_invite` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/deletion-inventory` | R/L | `backend/app/main.py:5088` / `parent_gallery_deletion_inventory` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/unlink-inventory` | R/L | `backend/app/main.py:5120` / `parent_gallery_client_unlink_inventory` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}` | R/G | `backend/app/main.py:5172` / `delete_parent_gallery` | db_session | ver matriz |
| `GET /admin/gallery-lifecycle-operations/{operation_id}` | R/L | `backend/app/main.py:5229` / `gallery_lifecycle_operation_status` | db_session | ver matriz |
| `POST /admin/gallery-lifecycle-operations/{operation_id}/retry` | R/L | `backend/app/main.py:5241` / `retry_gallery_lifecycle_operation` | db_session | ver matriz |
| `POST /admin/gallery-lifecycle-operations/{operation_id}/cancel` | R/L | `backend/app/main.py:5272` / `cancel_gallery_lifecycle_operation` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/clone` | R/G | `backend/app/main.py:5339` / `clone_derived_gallery` | db_session | ver matriz |
| `POST /admin/clients/{client_id}/phone/challenge` | R/C | `backend/app/main.py:5361` / `challenge_client_phone` | db_session | ver matriz |
| `POST /admin/clients/{client_id}/phone` | R/C | `backend/app/main.py:5382` / `change_client_phone` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients` | R/G | `backend/app/main.py:5414` / `parent_gallery_clients` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}` | R/G | `backend/app/main.py:5666` / `link_admin_client_to_parent_gallery` | db_session | ver matriz |
| `PATCH /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/access` | R/G | `backend/app/main.py:5695` / `update_admin_client_gallery_access` | db_session | ver matriz |
| `DELETE /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}` | R/L | `backend/app/main.py:5736` / `unlink_admin_client_from_parent_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/selection` | R/S | `backend/app/main.py:5830` / `selection_detail` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/selection/export.{format}` | R/L | `backend/app/main.py:5962` / `export_selection` | db_session | ver matriz |
| `GET /admin/orders/{order_id}/selection/export.{format}` | R/L | `backend/app/main.py:6058` / `export_finalized_order` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/selection/export.{format}` | R/L | `backend/app/main.py:6080` / `export_canonical_selection` | db_session | ver matriz |
| `POST /admin/parent-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:6173` / `register_photo_asset` | db_session | ver matriz |
| `PUT /admin/photo-assets/{photo_id}/source` | R/G | `backend/app/main.py:6189` / `import_photo_source` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/media-status` | R/G | `backend/app/main.py:6295` / `photo_media_status` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/facial-analysis` | R/F | `backend/app/main.py:6310` / `admin_photo_facial_analysis` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/preview` | R/G | `backend/app/main.py:6334` / `admin_photo_preview` | db_session | ver matriz |
| `GET /admin/photo-assets/{photo_id}/watermarked-preview` | R/G | `backend/app/main.py:6363` / `admin_watermarked_photo_preview` | db_session | ver matriz |
| `GET /admin/purchases` | R/S | `backend/app/main.py:6394` / `admin_purchase_history` | db_session | ver matriz |
| `GET /admin/pricing-presets` | R/K | `backend/app/main.py:6522` / `list_progressive_pricing_presets` | db_session | ver matriz |
| `POST /admin/pricing-presets` | R/K | `backend/app/main.py:6538` / `create_progressive_pricing_preset` | db_session | ver matriz |
| `PUT /admin/pricing-presets/{preset_id}` | R/K | `backend/app/main.py:6575` / `update_progressive_pricing_preset` | db_session | ver matriz |
| `DELETE /admin/pricing-presets/{preset_id}` | R/K | `backend/app/main.py:6602` / `deactivate_progressive_pricing_preset` | db_session | ver matriz |
| `POST /admin/pricing-presets/{preset_id}/activate` | R/K | `backend/app/main.py:6618` / `activate_progressive_pricing_preset` | db_session | ver matriz |
| `GET /admin/pricing-presets/{preset_id}/quote` | R/K | `backend/app/main.py:6635` / `simulate_progressive_pricing_preset` | db_session | ver matriz |
| `GET /admin/parent-galleries/{parent_gallery_id}/pricing` | R/K | `backend/app/main.py:6849` / `admin_parent_gallery_pricing` | db_session | ver matriz |
| `PUT /admin/parent-galleries/{parent_gallery_id}/pricing` | R/K | `backend/app/main.py:6859` / `save_admin_parent_gallery_pricing` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/pricing` | R/K | `backend/app/main.py:6878` / `admin_gallery_pricing` | db_session | ver matriz |
| `PUT /admin/derived-galleries/{gallery_id}/pricing` | R/K | `backend/app/main.py:6897` / `save_admin_gallery_pricing` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/orders` | R/S | `backend/app/main.py:6914` / `admin_gallery_orders` | db_session | ver matriz |
| `POST /admin/derived-galleries` | R/G | `backend/app/main.py:6981` / `create_derived_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:7025` / `private_gallery_link_status` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:7069` / `issue_private_gallery_link` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/link/rotate` | R/G | `backend/app/main.py:7086` / `rotate_private_gallery_link` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/link` | R/G | `backend/app/main.py:7106` / `revoke_private_gallery_link` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/invite/rotate` | R/G | `backend/app/main.py:7124` / `rotate_private_gallery_invite` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/invite` | R/G | `backend/app/main.py:7140` / `revoke_private_gallery_invite` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/members` | R/G | `backend/app/main.py:7202` / `private_gallery_members` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members` | R/G | `backend/app/main.py:7269` / `add_private_gallery_member` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members/{client_id}/block` | R/G | `backend/app/main.py:7433` / `block_private_gallery_member` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/members/{client_id}/unblock` | R/G | `backend/app/main.py:7452` / `unblock_private_gallery_member` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/members/{client_id}` | R/G | `backend/app/main.py:7471` / `unlink_private_gallery_member` | db_session | ver matriz |
| `GET /admin/notifications` | R/N | `backend/app/main.py:7490` / `admin_gallery_membership_notifications` | db_session | ver matriz |
| `POST /admin/notifications/{notification_id}/read` | R/N | `backend/app/main.py:7550` / `read_admin_gallery_membership_notification` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/upload-batches` | R/G | `backend/app/main.py:7564` / `list_private_upload_batches` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/upload-batches` | R/G | `backend/app/main.py:7577` / `begin_private_upload_batch` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/upload-batches/{batch_id}/close` | R/G | `backend/app/main.py:7592` / `finish_private_upload_batch` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/folders` | R/G | `backend/app/main.py:7608` / `admin_private_gallery_folders` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/folders` | R/G | `backend/app/main.py:7650` / `create_private_gallery_folder` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/photos` | R/G | `backend/app/main.py:7681` / `admin_private_gallery_photos` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/photos` | R/G | `backend/app/main.py:7880` / `add_admin_private_gallery_photos` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/photos/{photo_id}` | R/L | `backend/app/main.py:7900` / `remove_admin_private_gallery_photo` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:7967` / `delete_derived_gallery` | db_session | ver matriz |
| `GET /admin/derived-galleries` | R/G | `backend/app/main.py:8019` / `list_derived_galleries` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:8074` / `derived_gallery_detail` | db_session | ver matriz |
| `PATCH /admin/derived-galleries/{gallery_id}` | R/G | `backend/app/main.py:8145` / `update_derived_gallery` | db_session | ver matriz |
| `POST /admin/derived-galleries/{gallery_id}/renew` | R/G | `backend/app/main.py:8162` / `renew_gallery_selection` | db_session | ver matriz |
| `GET /admin/gallery-reopening-requests` | R/S | `backend/app/main.py:8208` / `list_gallery_reopening_requests` | db_session | ver matriz |
| `POST /admin/gallery-reopening-requests/{request_id}/decision` | R/S | `backend/app/main.py:8256` / `decide_gallery_reopening_request` | db_session | ver matriz |
| `POST /admin/gallery-reopening-notifications/{notification_id}/retry` | R/N | `backend/app/main.py:8298` / `retry_gallery_reopening_notification` | db_session | ver matriz |
| `GET /admin/statistics` | R/L | `backend/app/main.py:8321` / `admin_statistics` | db_session | ver matriz |
| `GET /admin/statistics/filters` | R/L | `backend/app/main.py:8367` / `admin_statistics_filters` | db_session | ver matriz |
| `GET /admin/statistics/selected-not-purchased.txt` | R/L | `backend/app/main.py:8396` / `export_selected_not_purchased_txt` | db_session | ver matriz |
| `GET /admin/statistics/purchased.txt` | R/L | `backend/app/main.py:8422` / `export_purchased_txt` | db_session | ver matriz |
| `GET /library` | R/G | `backend/app/main.py:8448` / `client_library` | db_session | ver matriz |
| `GET /library/cart` | R/S | `backend/app/main.py:8785` / `unified_cart` | db_session | ver matriz |
| `POST /library/cart/prepare` | R/S | `backend/app/main.py:8790` / `prepare_unified_cart` | db_session | ver matriz |
| `POST /library/cart/{gallery_id}/finalize` | R/S | `backend/app/main.py:8808` / `finalize_unified_selection` | db_session | ver matriz |
| `POST /library/payments/{group_id}/report` | R/S | `backend/app/main.py:8821` / `report_unified_payment` | db_session | ver matriz |
| `DELETE /library/cart/{gallery_id}` | R/S | `backend/app/main.py:8835` / `remove_unified_cart_group` | db_session | ver matriz |
| `DELETE /library/cart/{gallery_id}/photos/{photo_id}` | R/S | `backend/app/main.py:8865` / `remove_unified_cart_photo` | db_session | ver matriz |
| `GET /library/purchases` | R/S | `backend/app/main.py:8893` / `client_purchase_history` | db_session | ver matriz |
| `GET /library/purchases/items/{item_id}/preview` | R/S | `backend/app/main.py:9080` / `client_purchased_photo_preview` | db_session | ver matriz |
| `GET /library/history/items/{item_id}/preview` | R/S | `backend/app/main.py:9116` / `client_historical_preview` | db_session | ver matriz |
| `GET /library/history/items/{item_id}/delivery` | R/S | `backend/app/main.py:9128` / `client_historical_delivery` | db_session | ver matriz |
| `GET /gallery/{gallery_id}` | R/G | `backend/app/main.py:9153` / `gallery_area` | sem Depends na assinatura | ver matriz |
| `GET /gallery/{gallery_id}/photos` | R/G | `backend/app/main.py:9183` / `gallery_photos` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/folders` | R/G | `backend/app/main.py:9236` / `gallery_released_folders` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/review` | R/S | `backend/app/main.py:9284` / `gallery_review` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/cover-preview` | R/G | `backend/app/main.py:9412` / `client_gallery_cover_preview` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/photos/{photo_id}/preview` | R/G | `backend/app/main.py:9437` / `client_photo_preview` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:9480` / `select_photo` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:9557` / `select_photo_from_public_gallery` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:9614` / `unselect_photo_from_public_gallery` | db_session | ver matriz |
| `POST /public-gallery/access` | R/G | `backend/app/main.py:9696` / `access_public_gallery_with_session` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}` | R/G | `backend/app/main.py:9736` / `public_gallery_for_client` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-search` | R/F | `backend/app/main.py:9793` / `public_gallery_facial_search_availability` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos/{photo_id}/face-regions` | R/F | `backend/app/main.py:9832` / `public_photo_face_regions` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/face-region-searches` | R/F | `backend/app/main.py:9858` / `public_face_region_search` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/facial-searches` | R/F | `backend/app/main.py:9888` / `create_public_gallery_facial_search` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-searches/latest` | R/F | `backend/app/main.py:9960` / `latest_public_gallery_facial_search_result` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}` | R/F | `backend/app/main.py:9980` / `public_gallery_facial_search_result` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}` | R/F | `backend/app/main.py:10002` / `cancel_public_gallery_facial_search` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}/candidates/{photo_id}` | R/F | `backend/app/main.py:10032` / `reject_public_gallery_facial_candidate` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}/candidates/{photo_id}/selection` | R/F | `backend/app/main.py:10061` / `select_public_gallery_facial_candidate` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos` | R/G | `backend/app/main.py:10110` / `public_gallery_photos` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/cover-preview` | R/G | `backend/app/main.py:10224` / `public_gallery_cover_preview` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/photos/{photo_id}/preview` | R/G | `backend/app/main.py:10252` / `public_gallery_photo_preview` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:10308` / `favorite_canonical_photo` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:10340` / `unfavorite_canonical_photo` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/view` | R/S | `backend/app/main.py:10362` / `record_canonical_photo_view` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/photos/{photo_id}/comments` | R/S | `backend/app/main.py:10393` / `create_canonical_photo_comment` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/comments` | R/S | `backend/app/main.py:10419` / `canonical_client_comments` | db_session | ver matriz |
| `DELETE /public-galleries/{parent_gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:10450` / `remove_canonical_comment` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/photos/{photo_id}/selection` | R/S | `backend/app/main.py:10477` / `unselect_photo` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/cart` | R/S | `backend/app/main.py:10543` / `client_cart` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/reopening-requests` | R/S | `backend/app/main.py:10556` / `client_gallery_reopening_request` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/reopening-requests` | R/S | `backend/app/main.py:10579` / `request_gallery_reopening` | db_session | ver matriz |
| `GET /public-galleries/{parent_gallery_id}/reopening-requests` | R/S | `backend/app/main.py:10645` / `canonical_gallery_reopening_request` | db_session | ver matriz |
| `POST /public-galleries/{parent_gallery_id}/reopening-requests` | R/S | `backend/app/main.py:10667` / `request_canonical_gallery_reopening` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/checkout` | R/S | `backend/app/main.py:10728` / `checkout_gallery` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/orders/{order_id}/payment-communications` | R/S | `backend/app/main.py:10757` / `communicate_payment` | db_session | ver matriz |
| `POST /admin/payment-communications/{communication_id}/decision` | R/S | `backend/app/main.py:10856` / `decide_payment_communication` | db_session | ver matriz |
| `POST /admin/payment-communications/{communication_id}/correction` | R/S | `backend/app/main.py:10905` / `correct_payment_confirmation` | db_session | ver matriz |
| `PUT /admin/orders/{order_id}/delivery` | R/S | `backend/app/main.py:11023` / `update_order_delivery` | db_session | ver matriz |
| `POST /admin/orders/{order_id}/delivery/resend` | R/S | `backend/app/main.py:11039` / `resend_order_delivery` | db_session | ver matriz |
| `GET /push/subscription` | R/N | `backend/app/main.py:11061` / `push_subscription_state` | db_session | ver matriz |
| `POST /push/subscription` | R/N | `backend/app/main.py:11082` / `register_push_subscription` | db_session | ver matriz |
| `DELETE /push/subscription` | R/N | `backend/app/main.py:11109` / `unregister_push_subscription` | db_session | ver matriz |
| `GET /admin/notification-settings` | R/K | `backend/app/main.py:11137` / `list_notification_settings` | db_session | ver matriz |
| `PUT /admin/notification-settings/{event_type}` | R/K | `backend/app/main.py:11145` / `update_notification_setting` | db_session | ver matriz |
| `PUT /admin/payment-message-templates/{kind}` | R/K | `backend/app/main.py:11159` / `save_payment_template` | db_session | ver matriz |
| `GET /admin/payment-message-templates` | R/K | `backend/app/main.py:11176` / `list_payment_templates` | db_session | ver matriz |
| `GET /admin/removed-photo-movements` | R/L | `backend/app/main.py:11191` / `admin_removed_photo_movements` | db_session | ver matriz |
| `GET /admin/payment-communications` | R/S | `backend/app/main.py:11210` / `list_payment_communications` | db_session | ver matriz |
| `POST /admin/payment-notifications/{notification_id}/retry` | R/N | `backend/app/main.py:11777` / `retry_payment_notification` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/payment-communications` | R/S | `backend/app/main.py:11799` / `client_payment_communications` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/orders/{order_id}` | R/S | `backend/app/main.py:11819` / `client_pending_order` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:11893` / `favorite_photo` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/photos/{photo_id}/favorite` | R/S | `backend/app/main.py:11927` / `unfavorite_photo` | db_session | ver matriz |
| `POST /gallery/{gallery_id}/photos/{photo_id}/comments` | R/S | `backend/app/main.py:11948` / `create_photo_comment` | db_session | ver matriz |
| `GET /gallery/{gallery_id}/comments` | R/S | `backend/app/main.py:11979` / `client_comments` | db_session | ver matriz |
| `DELETE /gallery/{gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:12003` / `remove_own_comment` | db_session | ver matriz |
| `GET /admin/derived-galleries/{gallery_id}/comments` | R/S | `backend/app/main.py:12026` / `admin_comments` | db_session | ver matriz |
| `DELETE /admin/derived-galleries/{gallery_id}/comments/{comment_id}` | R/S | `backend/app/main.py:12054` / `remove_comment_as_admin` | db_session | ver matriz |
| `GET /admin/preview-adjustment/galleries/{gallery_id}/configuration` | R/P | `backend/app/preview_adjustment/api.py:34` / `configuration` | sem Depends na assinatura | ver matriz |
| `PATCH /admin/preview-adjustment/galleries/{gallery_id}/configuration` | R/P | `backend/app/preview_adjustment/api.py:49` / `save_configuration` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/galleries` | R/P | `backend/app/preview_adjustment/api.py:65` / `galleries` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/galleries/{gallery_id}` | R/P | `backend/app/preview_adjustment/api.py:84` / `gallery_progress` | sem Depends na assinatura | ver matriz |
| `POST /admin/preview-adjustment/galleries/{gallery_id}/enqueue` | R/P | `backend/app/preview_adjustment/api.py:127` / `enqueue_gallery` | sem Depends na assinatura | ver matriz |
| `GET /admin/preview-adjustment/photos/{photo_id}/{version}` | R/P | `backend/app/preview_adjustment/api.py:165` / `compare` | sem Depends na assinatura | ver matriz |

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
| `backend/app/admin_account.py:227` / `resend_security_challenge` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:273` / `issue_password_reset_email` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:280` / `issue_password_reset_email` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:301` / `challenge_target` | A | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:305` / `challenge_target` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/admin_account.py:314` / `token_target` | A | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:318` / `token_target` | A | query/ORM | `payload.get` | ver matriz |
| `backend/app/admin_account.py:340` / `issue_email_verification` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/admin_account.py:349` / `issue_email_verification` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:367` / `queue_previous_email_notice` | A | efeito potencial | `enqueue_email` | ver matriz |
| `backend/app/admin_account.py:392` / `active_admin_for_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/admin_account.py:113` / `_queue_admin_otp` | A | efeito potencial | `encrypt_otp` | ver matriz |
| `backend/app/admin_account.py:137` / `create_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:138` / `create_security_challenge` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/admin_account.py:152` / `create_security_challenge` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/admin_account.py:175` / `create_security_challenge` | A | efeito potencial | `encrypt_sensitive_payload` | ver matriz |
| `backend/app/admin_account.py:200` / `verify_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:231` / `resend_security_challenge` | A | gate | `require_security_owner` | ver matriz |
| `backend/app/admin_account.py:387` / `active_admin_for_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/admin_account.py:97` / `_queue_admin_otp` | A | query/ORM | `select` | ver matriz |
| `backend/app/admin_account.py:114` / `_queue_admin_otp` | A | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/admin_account.py:340` / `issue_email_verification` | A | query/ORM | `select` | ver matriz |
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
| `backend/app/auth.py:3008` / `audit` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3050` / `create_challenge` | A | produtor | `AuthChallenge` | ver matriz |
| `backend/app/auth.py:3062` / `create_challenge` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3078` / `enqueue_client_otp_delivery` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:3080` / `enqueue_client_otp_delivery` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3086` / `enqueue_client_otp_delivery` | A | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/auth.py:3113` / `enqueue_client_otp_delivery` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3149` / `resend_client_challenge` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:3150` / `resend_client_challenge` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3170` / `resend_client_challenge` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3186` / `resend_client_challenge` | A | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/auth.py:3197` / `consume_challenge` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3241` / `minimize_client_challenge_pii` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3261` / `cleanup_expired_client_otp_pii` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/auth.py:3308` / `create_session` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3319` / `create_session` | A | produtor | `AuthSession` | ver matriz |
| `backend/app/auth.py:3328` / `create_session` | A | query/ORM | `db.add` | ver matriz |
| `backend/app/auth.py:3346` / `current_session` | A | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/auth.py:3381` / `revoke_subject_sessions` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3388` / `revoke_subject_sessions` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:63` / `expired` | A | efeito potencial | `value.replace` | ver matriz |
| `backend/app/auth.py:82` / `_enable_sqlite_foreign_keys` | A | query/ORM | `cursor.execute` | ver matriz |
| `backend/app/auth.py:3008` / `audit` | A | produtor | `AuditEvent` | ver matriz |
| `backend/app/auth.py:3016` / `enforce_rate_limit` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3048` / `create_challenge` | A | gate | `require_client_channel` | ver matriz |
| `backend/app/auth.py:3098` / `enqueue_client_otp_delivery` | A | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/auth.py:3099` / `enqueue_client_otp_delivery` | A | efeito potencial | `encrypt_otp` | ver matriz |
| `backend/app/auth.py:3122` / `require_client_channel` | A | gate | `resolve_binding` | ver matriz |
| `backend/app/auth.py:3128` / `require_client_auth_tenant` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:3266` / `cleanup_expired_client_otp_pii` | A | query/ORM | `db.scalars` | ver matriz |
| `backend/app/auth.py:3276` / `cleanup_expired_client_otp_pii` | A | gate | `require_active_owner` | ver matriz |
| `backend/app/auth.py:3350` / `current_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:1307` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1340` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1351` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:3193` / `consume_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3292` / `create_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/auth.py:3293` / `create_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:307` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:307` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:314` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:315` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:321` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:322` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:558` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:559` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:566` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:567` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:573` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:574` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:811` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:812` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:844` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:845` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:877` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:878` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:934` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:935` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:986` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:990` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:999` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1004` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1215` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1216` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1224` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1225` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1231` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1232` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1313` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1324` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1341` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1356` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1363` / `_materialize_required_commercial_snapshots` | A | query/ORM | `session.get` | ver matriz |
| `backend/app/auth.py:1581` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1582` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1587` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:1588` / `<módulo>` | A | query/ORM | `text` | ver matriz |
| `backend/app/auth.py:3080` / `enqueue_client_otp_delivery` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3171` / `resend_client_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3242` / `minimize_client_challenge_pii` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3309` / `create_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3360` / `current_session` | A | gate | `require_admin_tenant` | ver matriz |
| `backend/app/auth.py:3361` / `current_session` | A | query/ORM | `db.get` | ver matriz |
| `backend/app/auth.py:3381` / `revoke_subject_sessions` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3389` / `revoke_subject_sessions` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3017` / `enforce_rate_limit` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3267` / `cleanup_expired_client_otp_pii` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3301` / `create_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3350` / `current_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3150` / `resend_client_challenge` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3368` / `current_session` | A | query/ORM | `db.scalar` | ver matriz |
| `backend/app/auth.py:3301` / `create_session` | A | query/ORM | `select` | ver matriz |
| `backend/app/auth.py:3368` / `current_session` | A | query/ORM | `select` | ver matriz |
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
| `backend/app/capacity_observability/queues.py:232` / `collect_adjustment_queue` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:61` / `_age` | O | efeito potencial | `timestamp.replace` | ver matriz |
| `backend/app/capacity_observability/queues.py:175` / `collect_facial_queues` | O | query/ORM | `rows.get` | ver matriz |
| `backend/app/capacity_observability/queues.py:172` / `collect_facial_queues` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/queues.py:209` / `collect_media_queue` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:216` / `collect_media_queue` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/queues.py:237` / `collect_adjustment_queue` | O | query/ORM | `db.execute` | ver matriz |
| `backend/app/capacity_observability/queues.py:155` / `collect_facial_queues` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:197` / `collect_media_queue` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:148` / `collect_facial_queues` | O | query/ORM | `select` | ver matriz |
| `backend/app/capacity_observability/queues.py:207` / `collect_media_queue` | O | query/ORM | `select` | ver matriz |
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
| `backend/app/facial/engine.py:69` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:78` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:88` / `replace_photo_index` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:105` / `replace_photo_index` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/engine.py:107` / `replace_photo_index` | F | gate | `media_namespace` | ver matriz |
| `backend/app/facial/engine.py:115` / `revalidate` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:116` / `revalidate` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:117` / `revalidate` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/engine.py:145` / `replace_photo_index` | F | efeito potencial | `json.dumps({'embedding': face.embedding, 'quality': assessment.encrypted_indicators()}, separators=(',', ':'), sort_keys=True).encode` | ver matriz |
| `backend/app/facial/engine.py:153` / `replace_photo_index` | F | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/facial/engine.py:194` / `replace_photo_index` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/engine.py:201` / `replace_photo_index` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/engine.py:231` / `search_gallery_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:237` / `search_gallery_index` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/engine.py:266` / `search_gallery_index` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/engine.py:269` / `search_gallery_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:270` / `search_gallery_index` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/engine.py:288` / `search_gallery_index` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/engine.py:321` / `search_gallery_index` | F | query/ORM | `best_by_photo.get` | ver matriz |
| `backend/app/facial/engine.py:171` / `replace_photo_index` | F | produtor | `PhotoFaceEmbedding` | ver matriz |
| `backend/app/facial/engine.py:70` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:79` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:89` / `replace_photo_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:279` / `search_gallery_index` | F | query/ORM | `allowed_fingerprints.get` | ver matriz |
| `backend/app/facial/engine.py:195` / `replace_photo_index` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/engine.py:148` / `replace_photo_index` | F | efeito potencial | `assessment.encrypted_indicators` | ver matriz |
| `backend/app/facial/engine.py:117` / `revalidate` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/engine.py:238` / `search_gallery_index` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/face_worker.py:35` / `record_provider_failure` | F | gate | `domain_session` | ver matriz |
| `backend/app/facial/face_worker.py:68` / `main` | F | gate | `domain_session` | ver matriz |
| `backend/app/facial/indexing.py:108` / `enqueue_photo_index_if_eligible` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/indexing.py:136` / `enqueue_photo_index_if_eligible` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/indexing.py:201` / `enqueue_gallery_backfill_page` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/indexing.py:237` / `enqueue_gallery_backfill_page` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/indexing.py:250` / `enqueue_gallery_backfill_page` | F | efeito potencial | `enqueue_photo_index_if_eligible` | ver matriz |
| `backend/app/facial/indexing.py:287` / `reconcile_gallery_index` | F | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/facial/indexing.py:322` / `reconcile_automatic_gallery_policies` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/indexing.py:64` / `preview_fingerprint` | F | efeito potencial | `path.open` | ver matriz |
| `backend/app/facial/indexing.py:154` / `enqueue_photo_index_if_eligible` | F | efeito potencial | `(repository or FacialJobRepository()).enqueue` | ver matriz |
| `backend/app/facial/indexing.py:353` / `reconcile_automatic_gallery_policies` | F | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/facial/indexing.py:66` / `preview_fingerprint` | F | query/ORM | `digest.update` | ver matriz |
| `backend/app/facial/indexing.py:137` / `enqueue_photo_index_if_eligible` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/indexing.py:323` / `reconcile_automatic_gallery_policies` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/indexing.py:207` / `enqueue_gallery_backfill_page` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:115` / `enqueue` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:120` / `enqueue` | F | produtor | `FacialJob` | ver matriz |
| `backend/app/facial/jobs.py:173` / `claim_next` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:312` / `_leased` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/jobs.py:313` / `_leased` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:334` / `release_denied` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:357` / `dispatch` | F | efeito potencial | `self._repository.enqueue` | ver matriz |
| `backend/app/facial/jobs.py:169` / `claim_next` | F | query/ORM | `FACIAL_JOB_KINDS_BY_CLASS.get` | ver matriz |
| `backend/app/facial/jobs.py:301` / `require_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/jobs.py:137` / `enqueue` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/jobs.py:140` / `enqueue` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/jobs.py:306` / `require_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/jobs.py:116` / `enqueue` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:157` / `claim_next` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:141` / `enqueue` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:334` / `release_denied` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/jobs.py:364` / `dispatch` | F | query/ORM | `job.get` | ver matriz |
| `backend/app/facial/jobs.py:314` / `_leased` | F | query/ORM | `select` | ver matriz |
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
| `backend/app/facial/lifecycle.py:340` / `cleanup_sources` | F | efeito potencial | `cleanup_upload_fragments` | ver matriz |
| `backend/app/facial/lifecycle.py:352` / `cleanup_upload_fragments` | F | query/ORM | `db.scalars` | ver matriz |
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
| `backend/app/facial/lifecycle.py:356` / `cleanup_upload_fragments` | F | gate | `require_single_tenant` | ver matriz |
| `backend/app/facial/lifecycle.py:369` / `cleanup_upload_fragments` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/lifecycle.py:374` / `cleanup_upload_fragments` | F | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/facial/lifecycle.py:255` / `cleanup_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:285` / `cleanup_source` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/lifecycle.py:352` / `cleanup_upload_fragments` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:373` / `cleanup_upload_fragments` | F | gate | `require_single_tenant` | ver matriz |
| `backend/app/facial/lifecycle.py:66` / `admit_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:268` / `cleanup_source` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/lifecycle.py:370` / `cleanup_upload_fragments` | F | efeito potencial | `(root / '.pyp-uploading').resolve` | ver matriz |
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
| `backend/app/facial/notifications.py:44` / `enqueue_search_notification` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:51` / `enqueue_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:67` / `enqueue_search_notification` | F | efeito potencial | `cipher.encrypt` | ver matriz |
| `backend/app/facial/notifications.py:71` / `enqueue_search_notification` | F | produtor | `FacialSearchNotificationOutbox` | ver matriz |
| `backend/app/facial/notifications.py:107` / `process_next_search_notification` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/notifications.py:123` / `process_next_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:221` / `notification_origin` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:222` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:223` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:224` / `notification_origin` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:225` / `notification_origin` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:240` / `cancel_pending_search_notifications` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:241` / `cancel_pending_search_notifications` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/notifications.py:45` / `enqueue_search_notification` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/notifications.py:148` / `process_next_search_notification` | F | gate | `provider_for` | ver matriz |
| `backend/app/facial/notifications.py:161` / `process_next_search_notification` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/notifications.py:162` / `process_next_search_notification` | F | efeito potencial | `active_provider.send_transactional` | ver matriz |
| `backend/app/facial/notifications.py:85` / `enqueue_search_notification` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/notifications.py:88` / `enqueue_search_notification` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/notifications.py:267` / `_notification_message` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/notifications.py:52` / `enqueue_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:225` / `notification_origin` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:242` / `cancel_pending_search_notifications` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:89` / `enqueue_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:108` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/notifications.py:124` / `process_next_search_notification` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:178` / `_utc` | F | efeito potencial | `value.replace` | ver matriz |
| `backend/app/facial/observability.py:233` / `collect_facial_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/observability.py:301` / `collect_facial_metrics` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/observability.py:233` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:320` / `collect_facial_metrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/observability.py:331` / `collect_facial_metrics` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/observability.py:302` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:321` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/observability.py:332` / `collect_facial_metrics` | F | query/ORM | `select` | ver matriz |
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
| `backend/app/facial/provider.py:198` / `observe_highres_path` | F | efeito potencial | `Image.open` | ver matriz |
| `backend/app/facial/provider.py:264` / `observe_highres_path` | F | query/ORM | `self.last_metrics.update` | ver matriz |
| `backend/app/facial/provider.py:269` / `observe_highres_path` | F | query/ORM | `self.last_metrics.update` | ver matriz |
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
| `backend/app/facial/regions.py:59` / `authorized_region` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:61` / `authorized_region` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/regions.py:73` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:76` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:77` / `region_embedding` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/regions.py:83` / `region_embedding` | F | efeito potencial | `cipher.decrypt` | ver matriz |
| `backend/app/facial/regions.py:99` / `photo_regions` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/regions.py:105` / `photo_regions` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/regions.py:103` / `photo_regions` | F | gate | `client_tenant_id` | ver matriz |
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
| `backend/app/facial/search.py:187` / `create_search_request` | F | produtor | `FacialSearchRequest` | ver matriz |
| `backend/app/facial/search.py:322` / `_build_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:498` / `read_latest_search_result` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:572` / `cancel_search_request` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search.py:577` / `cancel_search_request` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:617` / `reject_search_candidate` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:661` / `authorize_search_candidate_selection` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:705` / `_authorized_search_request` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search.py:70` / `_require_search_context` | F | gate | `client_tenant_id` | ver matriz |
| `backend/app/facial/search.py:240` / `create_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:241` / `create_search_request` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/search.py:244` / `create_search_request` | F | efeito potencial | `job_repository.enqueue` | ver matriz |
| `backend/app/facial/search.py:254` / `create_search_request` | F | efeito potencial | `job_repository.enqueue` | ver matriz |
| `backend/app/facial/search.py:264` / `create_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:304` / `_build_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:338` / `_build_snapshot` | F | produtor | `FacialSearchSnapshotItem` | ver matriz |
| `backend/app/facial/search.py:371` / `_retire_prior_searches` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:397` / `_retire_prior_searches` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search.py:402` / `_retire_prior_searches` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:412` / `_retire_prior_searches` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:470` / `read_search_result` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search.py:557` / `cancel_search_request` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:588` / `cancel_search_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:630` / `reject_search_candidate` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search.py:265` / `create_search_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:382` / `_retire_prior_searches` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:413` / `_retire_prior_searches` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:445` / `search_request_payload` | F | query/ORM | `_POLL_AFTER_MS.get` | ver matriz |
| `backend/app/facial/search.py:589` / `cancel_search_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:631` / `reject_search_candidate` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search.py:280` / `create_search_request` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search.py:573` / `cancel_search_request` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search.py:578` / `cancel_search_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:618` / `reject_search_candidate` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:662` / `authorize_search_candidate_selection` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:372` / `_retire_prior_searches` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:398` / `_retire_prior_searches` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search.py:403` / `_retire_prior_searches` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:323` / `_build_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:471` / `read_search_result` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:346` / `_build_snapshot` | F | query/ORM | `latest_by_photo.get` | ver matriz |
| `backend/app/facial/search.py:706` / `_authorized_search_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search.py:499` / `read_latest_search_result` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:71` / `process_claimed_search_job` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:296` / `_request_is_authorized` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/search_worker.py:316` / `_request_is_authorized` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:317` / `_request_is_authorized` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search_worker.py:325` / `_request_is_authorized` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:415` / `_snapshot_items` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:452` / `_delete_reference` | F | query/ORM | `store.delete` | ver matriz |
| `backend/app/facial/search_worker.py:474` / `_finish_request` | F | gate | `require_active_owner` | ver matriz |
| `backend/app/facial/search_worker.py:492` / `_finish_request` | F | query/ORM | `db.add` | ver matriz |
| `backend/app/facial/search_worker.py:502` / `_finish_request` | F | efeito potencial | `enqueue_search_notification` | ver matriz |
| `backend/app/facial/search_worker.py:210` / `process_claimed_search_job` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search_worker.py:219` / `process_claimed_search_job` | F | query/ORM | `db.add_all` | ver matriz |
| `backend/app/facial/search_worker.py:375` / `_refresh_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:419` / `_snapshot_items` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:476` / `_finish_request` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/search_worker.py:483` / `_finish_request` | F | query/ORM | `db.execute` | ver matriz |
| `backend/app/facial/search_worker.py:493` / `_finish_request` | F | produtor | `AuditEvent` | ver matriz |
| `backend/app/facial/search_worker.py:234` / `process_claimed_search_job` | F | efeito potencial | `repository.enqueue` | ver matriz |
| `backend/app/facial/search_worker.py:262` / `process_claimed_search_job` | F | query/ORM | `db.get` | ver matriz |
| `backend/app/facial/search_worker.py:276` / `process_claimed_search_job` | F | gate | `owned_record` | ver matriz |
| `backend/app/facial/search_worker.py:355` / `_refresh_snapshot` | F | query/ORM | `db.scalars` | ver matriz |
| `backend/app/facial/search_worker.py:393` / `_refresh_snapshot` | F | query/ORM | `latest_by_photo.get` | ver matriz |
| `backend/app/facial/search_worker.py:220` / `process_claimed_search_job` | F | produtor | `FacialSearchCandidate` | ver matriz |
| `backend/app/facial/search_worker.py:318` / `_request_is_authorized` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:211` / `process_claimed_search_job` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search_worker.py:476` / `_finish_request` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:483` / `_finish_request` | F | query/ORM | `delete` | ver matriz |
| `backend/app/facial/search_worker.py:376` / `_refresh_snapshot` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:420` / `_snapshot_items` | F | query/ORM | `select` | ver matriz |
| `backend/app/facial/search_worker.py:356` / `_refresh_snapshot` | F | query/ORM | `select` | ver matriz |
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
| `backend/app/facial/worker.py:52` / `process_claimed_index_job` | F | query/ORM | `db.scalar` | ver matriz |
| `backend/app/facial/worker.py:52` / `process_claimed_index_job` | F | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:32` / `folder_settings` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/folder_processing.py:37` / `folder_settings` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:52` / `effective_preview` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:67` / `configure_folder` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing.py:70` / `configure_folder` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing.py:80` / `configure_folder` | P | produtor | `FolderProcessingSettings` | ver matriz |
| `backend/app/folder_processing.py:81` / `configure_folder` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/folder_processing.py:89` / `configure_folder` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_processing.py:33` / `folder_settings` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:49` / `effective_preview` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:89` / `configure_folder` | P | query/ORM | `update` | ver matriz |
| `backend/app/folder_processing.py:70` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing.py:91` / `configure_folder` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:46` / `register_routes` | P | query/ORM | `app.get` | ver matriz |
| `backend/app/folder_processing_api.py:38` / `folder_or_404` | P | gate | `owned_record` | ver matriz |
| `backend/app/folder_processing_api.py:41` / `folder_or_404` | P | query/ORM | `db.get` | ver matriz |
| `backend/app/folder_processing_api.py:60` / `configuration` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:53` / `configuration` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/folder_processing_api.py:124` / `enqueue_folder_preview` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:150` / `reprocess_folder_facial` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/folder_processing_api.py:152` / `reprocess_folder_facial` | P | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/folder_processing_api.py:88` / `configuration` | P | query/ORM | `preview_counts.get` | ver matriz |
| `backend/app/folder_processing_api.py:125` / `enqueue_folder_preview` | P | efeito potencial | `enqueue_preview` | ver matriz |
| `backend/app/folder_processing_api.py:55` / `configuration` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/folder_processing_api.py:53` / `configuration` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:120` / `enqueue_folder_preview` | P | query/ORM | `select` | ver matriz |
| `backend/app/folder_processing_api.py:147` / `reprocess_folder_facial` | P | query/ORM | `select` | ver matriz |
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
| `backend/app/homolog_cleanup.py:148` / `inventory` | L | gate | `require_single_tenant` | ver matriz |
| `backend/app/homolog_cleanup.py:205` / `execute` | L | query/ORM | `connection.get_execution_options().get` | ver matriz |
| `backend/app/homolog_cleanup.py:206` / `execute` | L | query/ORM | `schema_map.get` | ver matriz |
| `backend/app/homolog_cleanup.py:210` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:211` / `execute` | L | gate | `require_single_tenant` | ver matriz |
| `backend/app/homolog_cleanup.py:224` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:225` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:226` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:229` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:234` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:235` / `execute` | L | gate | `require_single_tenant` | ver matriz |
| `backend/app/homolog_cleanup.py:210` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:214` / `execute` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:216` / `execute` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:228` / `execute` | L | query/ORM | `db.execute` | ver matriz |
| `backend/app/homolog_cleanup.py:234` / `execute` | L | query/ORM | `text` | ver matriz |
| `backend/app/homolog_cleanup.py:100` / `_count` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:103` / `_count` | L | query/ORM | `db.scalar` | ver matriz |
| `backend/app/homolog_cleanup.py:191` / `_clear_media_root` | L | efeito potencial | `entry.unlink` | ver matriz |
| `backend/app/homolog_cleanup.py:228` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:255` / `operational_delete_order` | L | query/ORM | `targets.add` | ver matriz |
| `backend/app/homolog_cleanup.py:224` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:225` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:226` / `execute` | L | query/ORM | `update` | ver matriz |
| `backend/app/homolog_cleanup.py:229` / `execute` | L | query/ORM | `delete` | ver matriz |
| `backend/app/homolog_cleanup.py:214` / `execute` | L | query/ORM | `select` | ver matriz |
| `backend/app/homolog_cleanup.py:216` / `execute` | L | query/ORM | `select` | ver matriz |
| `backend/app/installation_operator.py:14` / `operator_is_active` | O | query/ORM | `db.scalar` | ver matriz |
| `backend/app/installation_operator.py:21` / `require_operator` | O | gate | `operator_is_active` | ver matriz |
| `backend/app/installation_operator.py:14` / `operator_is_active` | O | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1225` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:1267` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:1329` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2024` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2065` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2071` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2092` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2109` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2358` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2370` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2450` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2515` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2576` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2586` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2599` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2627` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2690` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2702` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:2827` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:2846` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3048` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3151` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3195` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3288` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:3303` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3355` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3459` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3598` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3610` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3683` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3849` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3872` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:3942` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4075` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4246` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4317` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4352` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4397` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4491` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4789` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:4879` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:4992` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5087` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5119` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5168` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5228` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5413` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5732` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:5829` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:5961` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6057` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6079` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6294` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6309` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6333` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6362` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6393` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6521` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6601` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:6634` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6848` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6877` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:6913` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7024` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7102` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7136` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7201` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7470` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7489` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7563` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7607` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7680` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:7899` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:7966` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:8018` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8073` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8207` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8320` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8366` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8395` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8421` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8447` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8784` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:8834` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:8864` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:8892` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9079` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9115` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9127` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9152` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9182` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9235` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9283` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9411` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9436` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9613` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:9735` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9792` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9831` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9957` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9977` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:9999` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10028` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10109` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10223` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10251` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10336` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10418` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10446` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10474` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:10542` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10555` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:10644` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11060` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11108` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:11136` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11175` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11190` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11209` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11798` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11818` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:11924` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:11978` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12002` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:12025` / `<módulo>` | X | query/ORM | `app.get` | ver matriz |
| `backend/app/main.py:12050` / `<módulo>` | X | query/ORM | `app.delete` | ver matriz |
| `backend/app/main.py:499` / `read_bounded_body` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:920` / `directory_tenant_id` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:927` / `require_same_origin` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:956` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:957` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:966` / `derived_gallery_for_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:985` / `require_parent_gallery_mutable` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:999` / `require_derived_gallery_mutable` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1008` / `assigned_photo_for_gallery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:1009` / `assigned_photo_for_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1024` / `assigned_photo_for_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1098` / `_client_journey_destination` | X | query/ORM | `private_by_parent.get` | ver matriz |
| `backend/app/main.py:1115` / `statistics_data` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:1232` / `whatsapp_webhook` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1233` / `whatsapp_webhook` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:1269` / `admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1288` / `update_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1298` / `refresh_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1310` / `pair_admin_whatsapp_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1335` / `admin_whatsapp_deliveries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1363` / `retry_admin_whatsapp_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:1364` / `retry_admin_whatsapp_delivery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1426` / `validate_client_capability_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1453` / `client_challenge_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1497` / `client_challenge` | X | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/main.py:1509` / `client_resend` | X | efeito potencial | `resend_client_challenge` | ver matriz |
| `backend/app/main.py:1522` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1794` / `admin_password` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1822` / `admin_totp` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1835` / `admin_totp` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1870` / `admin_recovery_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1948` / `admin_recovery_reset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1982` / `confirm_admin_email` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1995` / `confirm_admin_email` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2074` / `admin_email_channel` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2132` / `admin_global_pix_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2169` / `admin_global_pix_confirm` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2170` / `admin_global_pix_confirm` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2363` / `public_branding` | X | gate | `branding_tenant_id` | ver matriz |
| `backend/app/main.py:2366` / `public_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2374` / `admin_branding` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2375` / `admin_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2384` / `update_admin_branding` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2385` / `update_admin_branding` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2399` / `update_visual_protection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2400` / `update_visual_protection` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2426` / `upload_branding_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2435` / `upload_branding_asset` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:2436` / `upload_branding_asset` | X | efeito potencial | `temporary.write_bytes` | ver matriz |
| `backend/app/main.py:2437` / `upload_branding_asset` | X | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/main.py:2438` / `upload_branding_asset` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2457` / `public_branding_asset` | X | gate | `branding_tenant_id` | ver matriz |
| `backend/app/main.py:2460` / `public_branding_asset` | X | gate | `branding_settings` | ver matriz |
| `backend/app/main.py:2482` / `public_branding_asset` | X | query/ORM | `{'.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon'}.get` | ver matriz |
| `backend/app/main.py:2520` / `admin_validation_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2592` / `admin_capacity_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2607` / `admin_facial_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2620` / `admin_facial_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2635` / `admin_clients` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2646` / `create_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2652` / `create_client` | X | produtor | `Client` | ver matriz |
| `backend/app/main.py:2653` / `create_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:2655` / `create_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:2680` / `update_client_name` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2681` / `update_client_name` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2694` / `get_client_deletion_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2696` / `get_client_deletion_inventory` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:2706` / `delete_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2831` / `admin_parent_galleries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2833` / `admin_parent_galleries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2856` / `parent_gallery_overview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2860` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2909` / `_parent_gallery_or_404` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:2945` / `_active_gallery_capability` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2956` / `_gallery_cover_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2976` / `_cover_preview_url` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2988` / `_cover_derivative` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2996` / `_client_preview_derivative` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3020` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3021` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3030` / `_cover_assets_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3036` / `_cover_assets_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:3043` / `_cover_assets_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3053` / `parent_gallery_editor` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3155` / `parent_gallery_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3185` / `update_parent_gallery_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3199` / `parent_gallery_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3229` / `parent_gallery_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3260` / `set_parent_gallery_cover` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3263` / `set_parent_gallery_cover` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3294` / `clear_parent_gallery_cover` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3307` / `parent_gallery_sales` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3335` / `update_parent_gallery_sales` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3359` / `parent_gallery_details` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3423` / `register_parent_gallery_cover_photo` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3432` / `register_parent_gallery_cover_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3465` / `admin_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3484` / `prepare_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3515` / `activate_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3554` / `suspend_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3579` / `revoke_parent_gallery_facial_policy` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3604` / `admin_parent_gallery_facial_cleanup_proof` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3618` / `admin_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3687` / `admin_private_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3761` / `retry_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3800` / `reprocess_parent_gallery_facial_index` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3853` / `admin_parent_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3857` / `admin_parent_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3879` / `admin_parent_gallery_available_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:3950` / `admin_parent_gallery_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4034` / `create_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4039` / `create_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4047` / `create_photo_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:4055` / `create_photo_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4065` / `_admin_linked_gallery_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4080` / `admin_client_restricted_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4133` / `create_admin_client_restricted_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4142` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4145` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4158` / `create_admin_client_restricted_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4163` / `create_admin_client_restricted_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:4169` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4171` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4189` / `grant_restricted_folder_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4191` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4204` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4254` / `revoke_restricted_folder_client` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4256` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4257` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4266` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4277` / `revoke_restricted_folder_client` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4284` / `revoke_restricted_folder_client` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:4297` / `rename_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4299` / `rename_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4321` / `delete_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4323` / `delete_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4326` / `delete_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4345` / `delete_photo_folder` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:4346` / `delete_photo_folder` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:4357` / `admin_photo_folder_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4368` / `admin_photo_folder_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4405` / `delete_folder_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4407` / `delete_folder_photo_asset` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4410` / `delete_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4428` / `delete_folder_photo_asset` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:4436` / `_delete_photo_records` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:4455` / `_delete_photo_records` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4458` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4459` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4460` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4461` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4462` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4465` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4466` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4467` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4468` / `_delete_photo_records` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4477` / `_delete_photo_records` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:4500` / `delete_folder_photo_assets` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4502` / `delete_folder_photo_assets` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4533` / `register_folder_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4535` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4558` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4572` / `register_folder_photo_asset` | X | produtor | `PhotoAsset` | ver matriz |
| `backend/app/main.py:4581` / `register_folder_photo_asset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4593` / `_publish_photo_folder` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:4661` / `publish_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4663` / `publish_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4673` / `publish_photo_folder` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:4684` / `publish_parent_gallery_ready_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4717` / `release_photo_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4727` / `release_photo_folder` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4737` / `release_photo_folder` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:4744` / `create_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4746` / `create_parent_gallery` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:4748` / `create_parent_gallery` | X | produtor | `ParentGallery` | ver matriz |
| `backend/app/main.py:4749` / `create_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4793` / `parent_gallery_public_link_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4825` / `issue_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4855` / `rotate_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4886` / `revoke_parent_gallery_public_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4941` / `issue_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:4944` / `issue_parent_gallery_client_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4968` / `rotate_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5002` / `revoke_parent_gallery_client_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5021` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:5094` / `parent_gallery_deletion_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5129` / `parent_gallery_client_unlink_inventory` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5132` / `parent_gallery_client_unlink_inventory` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5133` / `parent_gallery_client_unlink_inventory` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5177` / `delete_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5185` / `delete_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5202` / `delete_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5209` / `delete_parent_gallery` | X | produtor | `GalleryLifecycleOperation` | ver matriz |
| `backend/app/main.py:5221` / `delete_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5232` / `gallery_lifecycle_operation_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5234` / `gallery_lifecycle_operation_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5246` / `retry_gallery_lifecycle_operation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5248` / `retry_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5275` / `cancel_gallery_lifecycle_operation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5277` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5347` / `clone_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5365` / `challenge_client_phone` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5366` / `challenge_client_phone` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5377` / `challenge_client_phone` | X | efeito potencial | `enqueue_client_otp_delivery` | ver matriz |
| `backend/app/main.py:5385` / `change_client_phone` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5386` / `change_client_phone` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5390` / `change_client_phone` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:5417` / `parent_gallery_clients` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5565` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5579` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5672` / `link_admin_client_to_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5702` / `update_admin_client_gallery_access` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5705` / `update_admin_client_gallery_access` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5711` / `update_admin_client_gallery_access` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5745` / `unlink_admin_client_from_parent_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5753` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5770` / `unlink_admin_client_from_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5771` / `unlink_admin_client_from_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5774` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5784` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5802` / `unlink_admin_client_from_parent_gallery` | X | produtor | `GalleryLifecycleOperation` | ver matriz |
| `backend/app/main.py:5822` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5836` / `selection_detail` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5838` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5851` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5926` / `_selection_html_preview` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:5927` / `_selection_html_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5944` / `_selection_html_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5969` / `export_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:5973` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6037` / `export_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6060` / `export_finalized_order` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6062` / `export_finalized_order` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6065` / `export_finalized_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6087` / `export_canonical_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6091` / `export_canonical_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6092` / `export_canonical_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6093` / `export_canonical_selection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6179` / `register_photo_asset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6193` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6195` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6210` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6241` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6260` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6288` / `import_photo_source` | X | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/main.py:6299` / `photo_media_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6303` / `photo_media_status` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6313` / `admin_photo_facial_analysis` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6339` / `admin_photo_preview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6341` / `admin_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6344` / `admin_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6368` / `admin_watermarked_photo_preview` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6370` / `admin_watermarked_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6373` / `admin_watermarked_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6401` / `admin_purchase_history` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6408` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6467` / `_pricing_preset_payload` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:6500` / `_replace_pricing_preset_tiers` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:6501` / `_replace_pricing_preset_tiers` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6507` / `_replace_pricing_preset_tiers` | X | query/ORM | `db.add_all` | ver matriz |
| `backend/app/main.py:6527` / `list_progressive_pricing_presets` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6543` / `create_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6545` / `create_progressive_pricing_preset` | X | produtor | `ProgressivePricingPreset` | ver matriz |
| `backend/app/main.py:6568` / `_pricing_preset_or_404` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6581` / `update_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6607` / `deactivate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6623` / `activate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6641` / `simulate_progressive_pricing_preset` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6832` / `save_parent_pricing` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6833` / `save_parent_pricing` | X | query/ORM | `db.add_all` | ver matriz |
| `backend/app/main.py:6852` / `admin_parent_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6865` / `save_admin_parent_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6881` / `admin_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6883` / `admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6886` / `admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6903` / `save_admin_gallery_pricing` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6919` / `admin_gallery_orders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6921` / `admin_gallery_orders` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6986` / `create_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6988` / `create_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6989` / `create_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7030` / `private_gallery_link_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7046` / `private_gallery_link_status` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7075` / `issue_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7092` / `rotate_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7109` / `revoke_private_gallery_link` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7111` / `revoke_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7130` / `rotate_private_gallery_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7145` / `revoke_private_gallery_invite` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7212` / `private_gallery_members` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7214` / `private_gallery_members` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7220` / `private_gallery_members` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7275` / `add_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7278` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7279` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7369` / `_change_private_member_status` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7406` / `_change_private_member_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7407` / `_change_private_member_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7439` / `block_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7458` / `unblock_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7477` / `unlink_private_gallery_member` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7505` / `admin_gallery_membership_notifications` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7555` / `read_admin_gallery_membership_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7566` / `list_private_upload_batches` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7569` / `list_private_upload_batches` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7579` / `begin_private_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7594` / `finish_private_upload_batch` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7611` / `admin_private_gallery_folders` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7656` / `create_private_gallery_folder` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7659` / `create_private_gallery_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7665` / `create_private_gallery_folder` | X | produtor | `PhotoFolder` | ver matriz |
| `backend/app/main.py:7673` / `create_private_gallery_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:7684` / `admin_private_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7686` / `admin_private_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7886` / `add_admin_private_gallery_photos` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7906` / `remove_admin_private_gallery_photo` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7909` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7936` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7970` / `delete_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:7972` / `delete_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7976` / `delete_derived_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7980` / `delete_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7995` / `delete_derived_gallery` | X | efeito potencial | `enqueue_file_cleanup` | ver matriz |
| `backend/app/main.py:8031` / `list_derived_galleries` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8077` / `derived_gallery_detail` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8079` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8083` / `derived_gallery_detail` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8088` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8089` / `derived_gallery_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8151` / `update_derived_gallery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8168` / `renew_gallery_selection` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8182` / `_reopening_request_payload` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8215` / `list_gallery_reopening_requests` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8262` / `decide_gallery_reopening_request` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8264` / `decide_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8303` / `retry_gallery_reopening_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8304` / `retry_gallery_reopening_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8335` / `admin_statistics` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8371` / `admin_statistics_filters` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8406` / `export_selected_not_purchased_txt` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8432` / `export_purchased_txt` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:8493` / `client_library` | X | query/ORM | `parent_ids.update` | ver matriz |
| `backend/app/main.py:8608` / `client_library` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8778` / `_commerce_client` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8839` / `remove_unified_cart_group` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8869` / `remove_unified_cart_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9053` / `_historical_item_for_client` | X | gate | `client_tenant_id` | ver matriz |
| `backend/app/main.py:9054` / `_historical_item_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9067` / `_historical_item_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9086` / `client_purchased_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9100` / `client_purchased_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9101` / `client_purchased_photo_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9246` / `gallery_released_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9321` / `gallery_review` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9422` / `client_gallery_cover_preview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:9445` / `client_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9458` / `client_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9488` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9630` / `unselect_photo_from_public_gallery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9759` / `public_gallery_for_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9917` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:10273` / `public_gallery_photo_preview` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10319` / `favorite_canonical_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10349` / `unfavorite_canonical_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10371` / `record_canonical_photo_view` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10404` / `create_canonical_photo_comment` | X | produtor | `PhotoComment` | ver matriz |
| `backend/app/main.py:10411` / `create_canonical_photo_comment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10434` / `canonical_client_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10456` / `remove_canonical_comment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10534` / `_canonical_cart_payload` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:10565` / `client_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10596` / `request_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10609` / `request_gallery_reopening` | X | produtor | `GalleryReopeningRequest` | ver matriz |
| `backend/app/main.py:10615` / `request_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10617` / `request_gallery_reopening` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:10618` / `request_gallery_reopening` | X | produtor | `GalleryReopeningNotificationOutbox` | ver matriz |
| `backend/app/main.py:10624` / `request_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10656` / `canonical_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10679` / `request_canonical_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10686` / `request_canonical_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10696` / `request_canonical_gallery_reopening` | X | produtor | `GalleryReopeningRequest` | ver matriz |
| `backend/app/main.py:10702` / `request_canonical_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10704` / `request_canonical_gallery_reopening` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:10705` / `request_canonical_gallery_reopening` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10735` / `checkout_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10767` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10776` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10794` / `communicate_payment` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10804` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10818` / `communicate_payment` | X | produtor | `PaymentCommunication` | ver matriz |
| `backend/app/main.py:10824` / `communicate_payment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10827` / `communicate_payment` | X | gate | `legacy_owned_photographer_phone` | ver matriz |
| `backend/app/main.py:10862` / `decide_payment_communication` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10871` / `decide_payment_communication` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10884` / `decide_payment_communication` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10911` / `correct_payment_confirmation` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:10918` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10930` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10937` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10954` / `correct_payment_confirmation` | X | query/ORM | `{'confirmed': 'confirmed', 'refused': 'cancelled'}.get` | ver matriz |
| `backend/app/main.py:10967` / `correct_payment_confirmation` | X | produtor | `PaymentConfirmationCorrection` | ver matriz |
| `backend/app/main.py:10976` / `correct_payment_confirmation` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11025` / `update_order_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11041` / `resend_order_delivery` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11066` / `push_subscription_state` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11115` / `unregister_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11118` / `unregister_push_subscription` | X | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/main.py:11138` / `list_notification_settings` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11179` / `list_payment_templates` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11201` / `admin_removed_photo_movements` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11226` / `list_payment_communications` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11780` / `retry_payment_notification` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:11781` / `retry_payment_notification` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11826` / `client_pending_order` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11899` / `favorite_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11905` / `favorite_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11933` / `unfavorite_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11958` / `create_photo_comment` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:11964` / `create_photo_comment` | X | produtor | `PhotoComment` | ver matriz |
| `backend/app/main.py:11971` / `create_photo_comment` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11985` / `client_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12009` / `remove_own_comment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:12029` / `admin_comments` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:12033` / `admin_comments` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:12057` / `remove_comment_as_admin` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:12059` / `remove_comment_as_admin` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:893` / `db_session` | X | gate | `domain_session` | ver matriz |
| `backend/app/main.py:909` / `require_installation_operator` | X | gate | `require_operator` | ver matriz |
| `backend/app/main.py:915` / `directory_tenant_id` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1063` / `_client_journey_destination` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1066` / `_client_journey_destination` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1080` / `_client_journey_destination` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1094` / `_client_journey_destination` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1146` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1167` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1171` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1187` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1192` / `statistics_data` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1246` / `whatsapp_webhook` | X | gate | `webhook_owner` | ver matriz |
| `backend/app/main.py:1271` / `admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1430` / `validate_client_capability_context` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:1542` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1607` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1752` / `client_verify` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:1806` / `admin_password` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:1828` / `admin_totp` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/main.py:1907` / `admin_recovery_resend` | X | efeito potencial | `resend_security_challenge` | ver matriz |
| `backend/app/main.py:1954` / `admin_recovery_reset` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1988` / `confirm_admin_email` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2038` / `logout` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2039` / `logout` | X | query/ORM | `request.cookies.get` | ver matriz |
| `backend/app/main.py:2042` / `logout` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2277` / `admin_email_change_challenge` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2342` / `_branding_payload` | X | query/ORM | `payload.update` | ver matriz |
| `backend/app/main.py:2404` / `update_visual_protection` | X | efeito potencial | `enqueue_derivatives` | ver matriz |
| `backend/app/main.py:2407` / `update_visual_protection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2430` / `upload_branding_asset` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:2475` / `public_branding_asset` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/main.py:2522` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2526` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2527` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2656` / `create_client` | X | produtor | `ClientPhone` | ver matriz |
| `backend/app/main.py:2817` / `_client_deletion_transaction_state` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2953` / `_gallery_cover_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3057` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3070` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3078` / `parent_gallery_editor` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3203` / `parent_gallery_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3212` / `parent_gallery_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3272` / `set_parent_gallery_cover` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3362` / `parent_gallery_details` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3365` / `parent_gallery_details` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3368` / `parent_gallery_details` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3440` / `register_parent_gallery_cover_photo` | X | produtor | `PhotoAsset` | ver matriz |
| `backend/app/main.py:3449` / `register_parent_gallery_cover_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:3485` / `prepare_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3516` / `activate_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3555` / `suspend_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3580` / `revoke_parent_gallery_facial_policy` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3691` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3696` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3710` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3718` / `admin_private_gallery_facial_index` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3855` / `admin_parent_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3883` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3952` / `admin_parent_gallery_folders` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3955` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3976` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4087` / `admin_client_restricted_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4099` / `admin_client_restricted_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4104` / `admin_client_restricted_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4150` / `create_admin_client_restricted_folder` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:4154` / `create_admin_client_restricted_folder` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4171` / `create_admin_client_restricted_folder` | X | produtor | `FolderClientGrant` | ver matriz |
| `backend/app/main.py:4209` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4216` / `grant_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4226` / `grant_restricted_folder_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4272` / `revoke_restricted_folder_client` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4336` / `delete_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4362` / `admin_photo_folder_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4371` / `admin_photo_folder_photos` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4448` / `_delete_photo_records` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4510` / `delete_folder_photo_assets` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4562` / `register_folder_photo_asset` | X | efeito potencial | `namespaced_upload_key` | ver matriz |
| `backend/app/main.py:4564` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4569` / `register_folder_photo_asset` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4584` / `register_folder_photo_asset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4600` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4688` / `publish_parent_gallery_ready_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4698` / `publish_parent_gallery_ready_photos` | X | efeito potencial | `_publish_photo_folder` | ver matriz |
| `backend/app/main.py:5047` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:5149` / `parent_gallery_client_unlink_inventory` | X | efeito potencial | `client_unlink_inventory` | ver matriz |
| `backend/app/main.py:5308` / `cancel_gallery_lifecycle_operation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5348` / `clone_derived_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5421` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5428` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5433` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5499` / `parent_gallery_clients` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5529` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5547` / `parent_gallery_clients` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:5586` / `parent_gallery_clients` | X | query/ORM | `clients_by_id.get` | ver matriz |
| `backend/app/main.py:5587` / `parent_gallery_clients` | X | query/ORM | `galleries_by_client.get` | ver matriz |
| `backend/app/main.py:5588` / `parent_gallery_clients` | X | query/ORM | `memberships_by_client.get` | ver matriz |
| `backend/app/main.py:5589` / `parent_gallery_clients` | X | query/ORM | `registrations_by_client.get` | ver matriz |
| `backend/app/main.py:5600` / `parent_gallery_clients` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:5602` / `parent_gallery_clients` | X | query/ORM | `phone_verification_by_client.get` | ver matriz |
| `backend/app/main.py:5617` / `parent_gallery_clients` | X | query/ORM | `latest_canonical_order_by_client.get` | ver matriz |
| `backend/app/main.py:5716` / `update_admin_client_gallery_access` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:5722` / `update_admin_client_gallery_access` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:5855` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5863` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5871` / `selection_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5893` / `selection_detail` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5999` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6043` / `export_selection` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6097` / `export_canonical_selection` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6150` / `export_canonical_selection` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:6248` / `import_photo_source` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:6273` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6284` / `import_photo_source` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6301` / `photo_media_status` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6315` / `admin_photo_facial_analysis` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6411` / `admin_purchase_history` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6415` / `admin_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6469` / `_pricing_preset_payload` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6551` / `create_progressive_pricing_preset` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:6644` / `simulate_progressive_pricing_preset` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6689` / `pricing_payload` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6905` / `save_admin_gallery_pricing` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6923` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7077` / `issue_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7094` / `rotate_private_gallery_link` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7131` / `rotate_private_gallery_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7146` / `revoke_private_gallery_invite` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7162` / `_private_member_payload` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7283` / `add_private_gallery_member` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7288` / `add_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7345` / `add_private_gallery_member` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:7416` / `_change_private_member_status` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:7440` / `block_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7459` / `unblock_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7478` / `unlink_private_gallery_member` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7516` / `admin_gallery_membership_notifications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7615` / `admin_private_gallery_folders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7834` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7887` / `add_admin_private_gallery_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:7917` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7928` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:7943` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:7946` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7954` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:7990` / `delete_derived_gallery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8005` / `gallery_operational_status` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8007` / `gallery_operational_status` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8034` / `list_derived_galleries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8040` / `list_derived_galleries` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8051` / `list_derived_galleries` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8093` / `derived_gallery_detail` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8104` / `derived_gallery_detail` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8221` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8273` / `decide_gallery_reopening_request` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:8274` / `decide_gallery_reopening_request` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:8373` / `admin_statistics_filters` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8375` / `admin_statistics_filters` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8381` / `admin_statistics_filters` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8454` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8464` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8510` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:8513` / `client_library` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:8533` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8554` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:8557` / `client_library` | X | query/ORM | `registrations_by_parent.get` | ver matriz |
| `backend/app/main.py:8613` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8622` / `client_library` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:8634` / `client_library` | X | query/ORM | `prepared_gallery_ids.update` | ver matriz |
| `backend/app/main.py:8644` / `client_library` | X | query/ORM | `prepared_gallery_ids.update` | ver matriz |
| `backend/app/main.py:8684` / `client_library` | X | query/ORM | `public_by_parent.get` | ver matriz |
| `backend/app/main.py:8685` / `client_library` | X | query/ORM | `private_by_parent.get` | ver matriz |
| `backend/app/main.py:8706` / `client_library` | X | query/ORM | `canonical_cart_groups.get` | ver matriz |
| `backend/app/main.py:8716` / `client_library` | X | query/ORM | `parents_by_id.get` | ver matriz |
| `backend/app/main.py:8855` / `remove_unified_cart_group` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8900` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8968` / `client_purchase_history` | X | query/ORM | `operational_galleries.get` | ver matriz |
| `backend/app/main.py:8969` / `client_purchase_history` | X | query/ORM | `canonical_parents.get` | ver matriz |
| `backend/app/main.py:9194` / `gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9301` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9327` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9335` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9343` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9468` / `client_photo_preview` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:9507` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9601` / `_operational_gallery_for_public_client` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:10130` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10146` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10163` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10325` / `favorite_canonical_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10355` / `unfavorite_canonical_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:10379` / `record_canonical_photo_view` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:10504` / `unselect_photo` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10505` / `unselect_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10705` / `request_canonical_gallery_reopening` | X | produtor | `GalleryReopeningNotificationOutbox` | ver matriz |
| `backend/app/main.py:10925` / `correct_payment_confirmation` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:10945` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11045` / `resend_order_delivery` | X | efeito potencial | `resend_delivery` | ver matriz |
| `backend/app/main.py:11086` / `register_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11112` / `unregister_push_subscription` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11257` / `list_payment_communications` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:11270` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11431` / `list_payment_communications` | X | query/ORM | `canonical_states.get` | ver matriz |
| `backend/app/main.py:11432` / `list_payment_communications` | X | query/ORM | `communications_by_order.get` | ver matriz |
| `backend/app/main.py:11464` / `list_payment_communications` | X | query/ORM | `items_by_order.get` | ver matriz |
| `backend/app/main.py:11849` / `client_pending_order` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11913` / `favorite_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:11941` / `unfavorite_photo` | X | query/ORM | `db.delete` | ver matriz |
| `backend/app/main.py:12031` / `admin_comments` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:477` / `validate_branding_asset` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:1116` / `statistics_data` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:1257` / `whatsapp_admin_payload` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:1300` / `refresh_admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1313` / `pair_admin_whatsapp_channel` | X | gate | `provider_for` | ver matriz |
| `backend/app/main.py:1351` / `admin_whatsapp_deliveries` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:1382` / `retry_admin_whatsapp_delivery` | X | efeito potencial | `updated_at.replace` | ver matriz |
| `backend/app/main.py:2078` / `admin_email_channel` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:2101` / `admin_security_summary` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:2136` / `admin_global_pix_challenge` | X | query/ORM | `configuration.get` | ver matriz |
| `backend/app/main.py:2403` / `update_visual_protection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2583` / `admin_installation_capabilities` | X | gate | `operator_is_active` | ver matriz |
| `backend/app/main.py:2708` / `delete_client` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:2866` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2869` / `parent_gallery_overview` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2875` / `parent_gallery_overview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3530` / `activate_parent_gallery_facial_policy` | X | efeito potencial | `enqueue_gallery_backfill_page` | ver matriz |
| `backend/app/main.py:3898` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:3969` / `admin_parent_gallery_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:3988` / `admin_parent_gallery_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:4221` / `grant_restricted_folder_client` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:4226` / `grant_restricted_folder_client` | X | produtor | `FolderClientGrant` | ver matriz |
| `backend/app/main.py:4485` / `_remove_photo_files` | X | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/main.py:4584` / `register_folder_photo_asset` | X | produtor | `PrivateUploadBatchAsset` | ver matriz |
| `backend/app/main.py:4596` / `_publish_photo_folder` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4604` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4627` / `_publish_photo_folder` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5060` / `lifecycle_operation_payload` | X | query/ORM | `manifest.get` | ver matriz |
| `backend/app/main.py:5179` / `delete_parent_gallery` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:5312` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `(operation.manifest or {}).get` | ver matriz |
| `backend/app/main.py:5313` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:5459` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5463` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5488` / `parent_gallery_clients` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:5590` / `parent_gallery_clients` | X | query/ORM | `projections.get` | ver matriz |
| `backend/app/main.py:5601` / `parent_gallery_clients` | X | query/ORM | `canonical_selected.get` | ver matriz |
| `backend/app/main.py:5618` / `parent_gallery_clients` | X | query/ORM | `canonical_communications.get` | ver matriz |
| `backend/app/main.py:5675` / `link_admin_client_to_parent_gallery` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:5747` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:5883` / `selection_detail` | X | query/ORM | `sales_by_photo.get` | ver matriz |
| `backend/app/main.py:5987` / `export_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6106` / `export_canonical_selection` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6205` / `import_photo_source` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:6413` / `admin_purchase_history` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:6509` / `_replace_pricing_preset_tiers` | X | produtor | `ProgressivePricingTier` | ver matriz |
| `backend/app/main.py:6528` / `list_progressive_pricing_presets` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6835` / `save_parent_pricing` | X | produtor | `PriceRule` | ver matriz |
| `backend/app/main.py:6931` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7172` / `_private_member_payload` | X | efeito potencial | `membership.unlinked_at.isoformat` | ver matriz |
| `backend/app/main.py:7221` / `private_gallery_members` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7506` / `admin_gallery_membership_notifications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7689` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7696` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7710` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7720` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7736` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7746` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7922` / `remove_admin_private_gallery_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:7929` / `remove_admin_private_gallery_photo` | X | produtor | `DerivedGalleryPhotoOrigin` | ver matriz |
| `backend/app/main.py:8217` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8496` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8501` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8671` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8687` / `client_library` | X | query/ORM | `galleries_by_id.get` | ver matriz |
| `backend/app/main.py:8703` / `client_library` | X | query/ORM | `carts_by_gallery.get` | ver matriz |
| `backend/app/main.py:8710` / `client_library` | X | query/ORM | `orders_by_gallery.get` | ver matriz |
| `backend/app/main.py:8712` / `client_library` | X | query/ORM | `canonical_orders_by_parent.get` | ver matriz |
| `backend/app/main.py:8923` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8937` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8952` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8962` / `client_purchase_history` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8972` / `client_purchase_history` | X | query/ORM | `history_by_item.get` | ver matriz |
| `backend/app/main.py:9261` / `gallery_released_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9469` / `client_photo_preview` | X | produtor | `PhotoView` | ver matriz |
| `backend/app/main.py:9913` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:9914` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:10325` / `favorite_canonical_photo` | X | produtor | `PhotoFavorite` | ver matriz |
| `backend/app/main.py:10379` / `record_canonical_photo_view` | X | produtor | `PhotoView` | ver matriz |
| `backend/app/main.py:10630` / `request_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10716` / `request_canonical_gallery_reopening` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10838` / `communicate_payment` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10887` / `decide_payment_communication` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:10993` / `correct_payment_confirmation` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:11183` / `list_payment_templates` | X | query/ORM | `configured.get` | ver matriz |
| `backend/app/main.py:11284` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11304` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11325` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11363` / `list_payment_communications` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:11396` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11459` / `list_payment_communications` | X | query/ORM | `scopes_by_communication.get` | ver matriz |
| `backend/app/main.py:11622` / `list_payment_communications` | X | query/ORM | `configured_templates.get` | ver matriz |
| `backend/app/main.py:11644` / `list_payment_communications` | X | query/ORM | `delivery_counts.get` | ver matriz |
| `backend/app/main.py:11914` / `favorite_photo` | X | produtor | `PhotoFavorite` | ver matriz |
| `backend/app/main.py:1426` / `validate_client_capability_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1577` / `client_verify` | X | produtor | `Client` | ver matriz |
| `backend/app/main.py:1582` / `client_verify` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:1584` / `client_verify` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:1614` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:1794` / `admin_password` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1870` / `admin_recovery_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1949` / `admin_recovery_reset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1983` / `confirm_admin_email` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1996` / `confirm_admin_email` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2494` / `public_branding_asset` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:2681` / `update_client_name` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2877` / `parent_gallery_overview` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:3909` / `admin_parent_gallery_available_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4221` / `grant_restricted_folder_client` | X | produtor | `GalleryClientState` | ver matriz |
| `backend/app/main.py:4233` / `grant_restricted_folder_client` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:4277` / `revoke_restricted_folder_client` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4359` / `admin_photo_folder_photos` | X | gate | `owned_record` | ver matriz |
| `backend/app/main.py:4467` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4468` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4558` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5320` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `previous_state.get` | ver matriz |
| `backend/app/main.py:5366` / `challenge_client_phone` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5386` / `change_client_phone` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5493` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5509` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5520` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5555` / `parent_gallery_clients` | X | query/ORM | `canonical_item_counts.get` | ver matriz |
| `backend/app/main.py:5559` / `parent_gallery_clients` | X | query/ORM | `canonical_group_scopes.get` | ver matriz |
| `backend/app/main.py:5809` / `unlink_admin_client_from_parent_gallery` | X | efeito potencial | `client_unlink_inventory` | ver matriz |
| `backend/app/main.py:6229` / `import_photo_source` | X | efeito potencial | `Image.open` | ver matriz |
| `backend/app/main.py:6249` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:6502` / `_replace_pricing_preset_tiers` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:6532` / `list_progressive_pricing_presets` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6757` / `save_parent_pricing` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:6832` / `save_parent_pricing` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:7390` / `_change_private_member_status` | X | efeito potencial | `unlink_private_membership` | ver matriz |
| `backend/app/main.py:7625` / `admin_private_gallery_folders` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7639` / `admin_private_gallery_folders` | X | query/ORM | `counts.get` | ver matriz |
| `backend/app/main.py:7789` / `admin_private_gallery_photos` | X | query/ORM | `state_priority.get` | ver matriz |
| `backend/app/main.py:8183` / `_reopening_request_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8230` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8237` / `list_gallery_reopening_requests` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8483` / `client_library` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:8693` / `client_library` | X | query/ORM | `public_row.get` | ver matriz |
| `backend/app/main.py:8698` / `client_library` | X | query/ORM | `private_row.get` | ver matriz |
| `backend/app/main.py:9068` / `_historical_item_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9210` / `gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:9353` / `gallery_review` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10136` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10152` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10177` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:10190` / `public_gallery_photos` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11066` / `push_subscription_state` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11266` / `list_payment_communications` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:11437` / `list_payment_communications` | X | query/ORM | `notifications_by_communication.get` | ver matriz |
| `backend/app/main.py:1063` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1067` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1081` / `_client_journey_destination` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1118` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1162` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1181` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1430` / `validate_client_capability_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1585` / `client_verify` | X | produtor | `ClientPhone` | ver matriz |
| `backend/app/main.py:1664` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2042` / `logout` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2278` / `admin_email_change_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2408` / `update_visual_protection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2522` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2526` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2535` / `admin_validation_summary` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:2540` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2543` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2551` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2555` / `admin_validation_summary` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:2594` / `admin_capacity_observability` | X | gate | `require_installation_operator` | ver matriz |
| `backend/app/main.py:2937` / `_active_gallery_capability` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3711` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3719` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4117` / `admin_client_restricted_folders` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:4448` / `_delete_photo_records` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4564` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5326` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `previous_state.get` | ver matriz |
| `backend/app/main.py:5536` / `parent_gallery_clients` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:5645` / `parent_gallery_clients` | X | query/ORM | `canonical_purchased.get` | ver matriz |
| `backend/app/main.py:5648` / `parent_gallery_clients` | X | query/ORM | `canonical_reopening.get` | ver matriz |
| `backend/app/main.py:5651` / `parent_gallery_clients` | X | query/ORM | `finalized_by_client.get` | ver matriz |
| `backend/app/main.py:5652` / `parent_gallery_clients` | X | query/ORM | `canonical_financial_by_client.get` | ver matriz |
| `backend/app/main.py:5900` / `selection_detail` | X | query/ORM | `sales_by_photo.get` | ver matriz |
| `backend/app/main.py:6274` / `import_photo_source` | X | gate | `directory_tenant_id` | ver matriz |
| `backend/app/main.py:6403` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7790` / `admin_private_gallery_photos` | X | query/ORM | `commercial_state_by_photo_client.get` | ver matriz |
| `backend/app/main.py:7811` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:7819` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:7827` / `admin_private_gallery_photos` | X | query/ORM | `client_names.get` | ver matriz |
| `backend/app/main.py:7850` / `admin_private_gallery_photos` | X | query/ORM | `origins_by_reference.get` | ver matriz |
| `backend/app/main.py:8005` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8007` / `gallery_operational_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8636` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:8646` / `client_library` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:9517` / `select_photo` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/main.py:9936` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:11455` / `list_payment_communications` | X | query/ORM | `notifications_by_communication.get` | ver matriz |
| `backend/app/main.py:11456` / `list_payment_communications` | X | query/ORM | `corrections_by_communication.get` | ver matriz |
| `backend/app/main.py:1010` / `assigned_photo_for_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1453` / `client_challenge_context` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1690` / `client_verify` | X | efeito potencial | `enqueue_membership_notification` | ver matriz |
| `backend/app/main.py:1822` / `admin_totp` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2132` / `admin_global_pix_challenge` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2169` / `admin_global_pix_confirm` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2170` / `admin_global_pix_confirm` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2403` / `update_visual_protection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2977` / `_cover_preview_url` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2988` / `_cover_derivative` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2997` / `_client_preview_derivative` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3022` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3031` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3433` / `register_parent_gallery_cover_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4040` / `create_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4065` / `_admin_linked_gallery_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4158` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4204` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4266` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4458` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4459` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4460` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4461` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4462` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:4466` / `_delete_photo_records` | X | query/ORM | `delete` | ver matriz |
| `backend/app/main.py:5464` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5641` / `parent_gallery_clients` | X | query/ORM | `restricted_available.get` | ver matriz |
| `backend/app/main.py:5928` / `_selection_html_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5945` / `_selection_html_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6038` / `export_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6093` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6241` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6262` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:6303` / `photo_media_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6345` / `admin_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6374` / `admin_watermarked_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6968` / `admin_gallery_orders` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/main.py:7047` / `private_gallery_link_status` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7660` / `create_private_gallery_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7800` / `admin_private_gallery_photos` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/main.py:7910` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7937` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8305` / `retry_gallery_reopening_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8759` / `client_library` | X | query/ORM | `canonical_orders_by_parent.get` | ver matriz |
| `backend/app/main.py:8839` / `remove_unified_cart_group` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8869` / `remove_unified_cart_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9055` / `_historical_item_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9489` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9517` / `select_photo` | X | produtor | `PhotoSelection` | ver matriz |
| `backend/app/main.py:9521` / `select_photo` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/main.py:9630` / `unselect_photo_from_public_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10319` / `favorite_canonical_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10349` / `unfavorite_canonical_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10371` / `record_canonical_photo_view` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10456` / `remove_canonical_comment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10768` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10919` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11827` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11906` / `favorite_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11934` / `unfavorite_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12010` / `remove_own_comment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12060` / `remove_comment_as_admin` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:915` / `directory_tenant_id` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1172` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1193` / `statistics_data` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1336` / `admin_whatsapp_deliveries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2818` / `_client_deletion_transaction_state` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3204` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3273` / `set_parent_gallery_cover` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3368` / `parent_gallery_details` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3692` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3697` / `admin_private_gallery_facial_index` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4099` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4216` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4272` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4371` / `admin_photo_folder_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4569` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4600` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5422` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5429` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5434` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5856` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5864` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6198` / `import_photo_source` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:6248` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6415` / `admin_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6470` / `_pricing_preset_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6645` / `simulate_progressive_pricing_preset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6690` / `pricing_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7284` / `add_private_gallery_member` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7835` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7918` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7947` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8034` / `list_derived_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8105` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8373` / `admin_statistics_filters` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8381` / `admin_statistics_filters` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8477` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8855` / `remove_unified_cart_group` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9190` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9243` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9297` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9508` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9903` / `create_public_gallery_facial_search` | X | query/ORM | `request.headers.get` | ver matriz |
| `backend/app/main.py:10506` / `unselect_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1025` / `assigned_photo_for_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1683` / `client_verify` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/main.py:2540` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2834` / `admin_parent_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2861` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2866` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2870` / `parent_gallery_overview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3020` / `_cover_assets_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3858` / `admin_parent_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3899` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4142` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4145` / `create_admin_client_restricted_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4191` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4256` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4257` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4280` / `revoke_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4326` / `delete_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4410` / `delete_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4463` / `_delete_photo_records` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4465` / `_delete_photo_records` | X | query/ORM | `update` | ver matriz |
| `backend/app/main.py:4535` / `register_folder_photo_asset` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4605` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4628` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5134` / `parent_gallery_client_unlink_inventory` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5186` / `delete_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5249` / `retry_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5278` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5314` / `cancel_gallery_lifecycle_operation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5459` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5488` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5565` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5579` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5705` / `update_admin_client_gallery_access` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5711` / `update_admin_client_gallery_access` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5754` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5785` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6065` / `export_finalized_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6260` / `import_photo_source` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6931` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7220` / `private_gallery_members` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7569` / `list_private_upload_batches` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7923` / `remove_admin_private_gallery_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7976` / `delete_derived_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8084` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8265` / `decide_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8497` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8502` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8938` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8953` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8963` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9087` / `client_purchased_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9446` / `client_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9459` / `client_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9759` / `public_gallery_for_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10274` / `public_gallery_photo_preview` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10434` / `canonical_client_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10566` / `client_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10597` / `request_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10656` / `canonical_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10679` / `request_canonical_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10686` / `request_canonical_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10777` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10805` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10839` / `communicate_payment` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10888` / `decide_payment_communication` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10931` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10938` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10994` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11986` / `client_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:12034` / `admin_comments` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3058` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3071` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3079` / `parent_gallery_editor` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3910` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3956` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4209` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4233` / `grant_restricted_folder_client` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4363` / `admin_photo_folder_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4689` / `publish_parent_gallery_ready_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5499` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5529` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5872` / `selection_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6097` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6758` / `save_parent_pricing` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6924` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7616` / `admin_private_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8052` / `list_derived_galleries` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8094` / `derived_gallery_detail` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8231` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8237` / `list_gallery_reopening_requests` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8274` / `decide_gallery_reopening_request` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8376` / `admin_statistics_filters` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8455` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8465` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8484` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8613` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8757` / `client_library` | X | query/ORM | `cart.get` | ver matriz |
| `backend/app/main.py:8901` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9015` / `client_purchase_history` | X | query/ORM | `communications_by_order.get` | ver matriz |
| `backend/app/main.py:9328` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9336` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9344` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10130` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10146` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10946` / `correct_payment_confirmation` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11266` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11270` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11850` / `client_pending_order` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:1258` / `whatsapp_admin_payload` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2079` / `admin_email_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2535` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2544` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2551` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2556` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3230` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3970` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4117` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4597` / `_publish_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5202` / `delete_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5775` / `unlink_admin_client_from_parent_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7711` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7721` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7737` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8637` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8924` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10631` / `request_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10716` / `request_canonical_gallery_reopening` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11285` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11305` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11326` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11397` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2527` / `admin_validation_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3213` / `parent_gallery_summary` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3884` / `admin_parent_gallery_available_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4087` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4336` / `delete_photo_folder` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5493` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6151` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7626` / `admin_private_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7801` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7990` / `delete_derived_gallery` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9211` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9354` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9521` / `select_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10137` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10153` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10178` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:10191` / `public_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11235` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3989` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5536` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5988` / `export_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6107` / `export_canonical_selection` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7697` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8647` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8672` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8908` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8911` / `client_purchase_history` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9262` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:3977` / `admin_parent_gallery_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:4104` / `admin_client_restricted_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5520` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:6969` / `admin_gallery_orders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2083` / `admin_email_channel` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:2957` / `_gallery_cover_photo` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7690` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7747` / `admin_private_gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9247` / `gallery_released_folders` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:5509` / `parent_gallery_clients` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:8534` / `client_library` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9195` / `gallery_photos` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:9302` / `gallery_review` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:11338` / `list_payment_communications` | X | query/ORM | `select` | ver matriz |
| `backend/app/main.py:7222` / `private_gallery_members` | X | query/ORM | `select` | ver matriz |
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
| `backend/app/notification_delivery.py:65` / `mirror_payment_projection` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:76` / `recipient_allowed` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_delivery.py:307` / `retry_payment_projection` | N | gate | `require_active_owner` | ver matriz |
| `backend/app/notification_delivery.py:308` / `retry_payment_projection` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:311` / `retry_payment_projection` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:52` / `utc` | N | efeito potencial | `value.replace` | ver matriz |
| `backend/app/notification_delivery.py:81` / `recipient_allowed` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:94` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:117` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:121` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:138` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:181` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:189` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:207` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:291` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:316` / `retry_payment_projection` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_delivery.py:95` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:101` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:102` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:143` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:153` / `recipient_allowed` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:166` / `process_next_notification` | N | query/ORM | `db.scalars` | ver matriz |
| `backend/app/notification_delivery.py:177` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:199` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:208` / `process_next_notification` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:222` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:65` / `mirror_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:89` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:149` / `recipient_allowed` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:202` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:308` / `retry_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:85` / `recipient_allowed` | N | gate | `require_admin_tenant` | ver matriz |
| `backend/app/notification_delivery.py:236` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:242` / `process_next_notification` | N | efeito potencial | `push_sender or send_push` | ver matriz |
| `backend/app/notification_delivery.py:247` / `process_next_notification` | N | gate | `provider_for` | ver matriz |
| `backend/app/notification_delivery.py:251` / `process_next_notification` | N | query/ORM | `db.get` | ver matriz |
| `backend/app/notification_delivery.py:263` / `process_next_notification` | N | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/notification_delivery.py:282` / `process_next_notification` | N | query/ORM | `db.execute` | ver matriz |
| `backend/app/notification_delivery.py:153` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:237` / `process_next_notification` | N | gate | `owned_record` | ver matriz |
| `backend/app/notification_delivery.py:242` / `process_next_notification` | N | efeito potencial | `decrypt_subscription` | ver matriz |
| `backend/app/notification_delivery.py:258` / `process_next_notification` | N | query/ORM | `db.scalar` | ver matriz |
| `backend/app/notification_delivery.py:122` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:189` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:291` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:316` / `retry_payment_projection` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:102` / `recipient_allowed` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:202` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:258` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:282` / `process_next_notification` | N | query/ORM | `update` | ver matriz |
| `backend/app/notification_delivery.py:166` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
| `backend/app/notification_delivery.py:181` / `process_next_notification` | N | query/ORM | `select` | ver matriz |
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
| `backend/app/ownership_schema.py:65` / `apply_ownership_constraints` | X | query/ORM | `metadata.info.get` | ver matriz |
| `backend/app/parent_registration.py:21` / `link_client_to_parent` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/parent_registration.py:22` / `link_client_to_parent` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/parent_registration.py:25` / `link_client_to_parent` | G | gate | `require_client_owner` | ver matriz |
| `backend/app/parent_registration.py:27` / `link_client_to_parent` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/parent_registration.py:40` / `link_client_to_parent` | G | produtor | `ParentGalleryRegistration` | ver matriz |
| `backend/app/parent_registration.py:46` / `link_client_to_parent` | G | query/ORM | `db.add` | ver matriz |
| `backend/app/parent_registration.py:49` / `link_client_to_parent` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/parent_registration.py:28` / `link_client_to_parent` | G | query/ORM | `select` | ver matriz |
| `backend/app/parent_registration.py:50` / `link_client_to_parent` | G | query/ORM | `select` | ver matriz |
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
| `backend/app/preview_adjustment/cleanup.py:62` / `cleanup` | P | gate | `require_single_tenant` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:63` / `cleanup` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:68` / `cleanup` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:72` / `cleanup` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:79` / `cleanup` | P | gate | `require_single_tenant` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:80` / `cleanup` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:77` / `cleanup` | P | gate | `require_single_tenant` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:78` / `cleanup` | P | efeito potencial | `path.unlink` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:80` / `cleanup` | P | query/ORM | `delete` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:63` / `cleanup` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:68` / `cleanup` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/cleanup.py:72` / `cleanup` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/engine.py:64` / `render` | P | efeito potencial | `Image.open` | ver matriz |
| `backend/app/preview_adjustment/service.py:56` / `settings` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:63` / `settings` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:70` / `configure` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:72` / `configure` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:122` / `inputs` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:125` / `inputs` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:141` / `inputs` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:160` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:170` / `adjustment_for` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:171` / `adjustment_for` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:178` / `enqueue` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:179` / `enqueue` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:196` / `enqueue` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:255` / `adjusted_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:260` / `adjusted_path` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:79` / `configure` | P | produtor | `GalleryPreviewSettings` | ver matriz |
| `backend/app/preview_adjustment/service.py:87` / `configure` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/preview_adjustment/service.py:97` / `configure` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:164` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:182` / `enqueue` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:205` / `enqueue` | P | produtor | `PreviewAdjustment` | ver matriz |
| `backend/app/preview_adjustment/service.py:206` / `enqueue` | P | query/ORM | `db.add` | ver matriz |
| `backend/app/preview_adjustment/service.py:216` / `enqueue_after_derivatives` | P | efeito potencial | `enqueue` | ver matriz |
| `backend/app/preview_adjustment/service.py:256` / `adjusted_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:270` / `presentation_path` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:306` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:307` / `process_one` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:309` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:57` / `settings` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:128` / `inputs` | P | query/ORM | `db.scalars` | ver matriz |
| `backend/app/preview_adjustment/service.py:158` / `photo_active` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:277` / `presentation_path` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:283` / `presentation_path` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:340` / `process_one` | P | produtor | `BrandingSettings` | ver matriz |
| `backend/app/preview_adjustment/service.py:359` / `process_one` | P | efeito potencial | `Image.open` | ver matriz |
| `backend/app/preview_adjustment/service.py:368` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:369` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:377` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:380` / `process_one` | P | gate | `adjustment_for` | ver matriz |
| `backend/app/preview_adjustment/service.py:397` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:406` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:407` / `process_one` | P | efeito potencial | `temporary.replace` | ver matriz |
| `backend/app/preview_adjustment/service.py:295` / `process_one` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:374` / `process_one` | P | query/ORM | `db.scalar` | ver matriz |
| `backend/app/preview_adjustment/service.py:378` / `process_one` | P | gate | `owned_record` | ver matriz |
| `backend/app/preview_adjustment/service.py:430` / `process_one` | P | query/ORM | `db.execute` | ver matriz |
| `backend/app/preview_adjustment/service.py:417` / `process_one` | P | gate | `require_active_owner` | ver matriz |
| `backend/app/preview_adjustment/service.py:418` / `process_one` | P | efeito potencial | `previous.unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:425` / `process_one` | P | efeito potencial | `output.with_suffix('.tmp').unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:426` / `process_one` | P | efeito potencial | `output.unlink` | ver matriz |
| `backend/app/preview_adjustment/service.py:73` / `configure` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:142` / `inputs` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:171` / `adjustment_for` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:179` / `enqueue` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:370` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:98` / `configure` | P | query/ORM | `update` | ver matriz |
| `backend/app/preview_adjustment/service.py:129` / `inputs` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:377` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:375` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:431` / `process_one` | P | query/ORM | `update` | ver matriz |
| `backend/app/preview_adjustment/service.py:310` / `process_one` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:103` / `configure` | P | query/ORM | `select` | ver matriz |
| `backend/app/preview_adjustment/service.py:296` / `process_one` | P | query/ORM | `select` | ver matriz |
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
| `backend/app/public_gallery_access.py:57` / `active_capability_by_id` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:67` / `active_registration` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:87` / `apply_public_gallery_access` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/public_gallery_access.py:90` / `apply_public_gallery_access` | G | gate | `owned_record` | ver matriz |
| `backend/app/public_gallery_access.py:157` / `require_public_gallery_browsing` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:229` / `authorized_canonical_photo` | G | query/ORM | `db.scalar` | ver matriz |
| `backend/app/public_gallery_access.py:51` / `active_capability_by_id` | G | query/ORM | `db.get` | ver matriz |
| `backend/app/public_gallery_access.py:157` / `require_public_gallery_browsing` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:173` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:196` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:203` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:58` / `active_capability_by_id` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:68` / `active_registration` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:170` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
| `backend/app/public_gallery_access.py:178` / `authorized_canonical_photos` | G | query/ORM | `select` | ver matriz |
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
| `backend/app/unified_checkout.py:51` / `communications_for_orders` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/unified_checkout.py:57` / `communications_for_orders` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:80` / `_materials` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:111` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:145` / `cart_payload` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:252` / `_valid_materials` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:298` / `prepare_group` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:299` / `prepare_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:302` / `prepare_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:354` / `prepare_group` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/unified_checkout.py:397` / `payment_scopes` | S | gate | `require_active_owner` | ver matriz |
| `backend/app/unified_checkout.py:404` / `payment_scopes` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:422` / `payment_scope` | S | query/ORM | `payment_scopes(db, {communication.payment_group_id}, tenant_id=communication.tenant_id).get` | ver matriz |
| `backend/app/unified_checkout.py:426` / `lock_payment_scope` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:429` / `lock_payment_scope` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:462` / `report_group` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:463` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:464` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:471` / `report_group` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:521` / `report_group` | S | produtor | `PaymentCommunication` | ver matriz |
| `backend/app/unified_checkout.py:527` / `report_group` | S | query/ORM | `db.add` | ver matriz |
| `backend/app/unified_checkout.py:538` / `finalize_selection` | S | gate | `client_tenant_id` | ver matriz |
| `backend/app/unified_checkout.py:539` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:540` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:544` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:565` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:579` / `finalize_selection` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/unified_checkout.py:583` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:83` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:92` / `_materials` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:105` / `_materials` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:115` / `_materials` | S | gate | `owned_record` | ver matriz |
| `backend/app/unified_checkout.py:150` / `cart_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:186` / `cart_payload` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:324` / `prepare_group` | S | produtor | `PaymentGroup` | ver matriz |
| `backend/app/unified_checkout.py:339` / `prepare_group` | S | query/ORM | `drafts.get` | ver matriz |
| `backend/app/unified_checkout.py:391` / `group_payload` | S | query/ORM | `group.pix_configuration_snapshot.get` | ver matriz |
| `backend/app/unified_checkout.py:436` / `lock_payment_scope` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:443` / `lock_payment_scope` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:484` / `report_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:517` / `report_group` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:574` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:575` / `finalize_selection` | S | query/ORM | `db.delete` | ver matriz |
| `backend/app/unified_checkout.py:174` / `cart_payload` | S | query/ORM | `folders.get` | ver matriz |
| `backend/app/unified_checkout.py:309` / `prepare_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:362` / `prepare_group` | S | query/ORM | `drafts.get` | ver matriz |
| `backend/app/unified_checkout.py:362` / `prepare_group` | S | produtor | `SaleOrder` | ver matriz |
| `backend/app/unified_checkout.py:402` / `payment_scopes` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:505` / `report_group` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:578` / `finalize_selection` | S | query/ORM | `db.execute` | ver matriz |
| `backend/app/unified_checkout.py:549` / `finalize_selection` | S | query/ORM | `(existing.price_rule_snapshot or {}).get` | ver matriz |
| `backend/app/unified_checkout.py:577` / `finalize_selection` | S | query/ORM | `db.scalar` | ver matriz |
| `backend/app/unified_checkout.py:163` / `cart_payload` | S | query/ORM | `db.scalars` | ver matriz |
| `backend/app/unified_checkout.py:58` / `communications_for_orders` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:402` / `payment_scopes` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:405` / `payment_scopes` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:429` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:472` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:544` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:583` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:84` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:106` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:151` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:187` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:437` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:518` / `report_group` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:574` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:111` / `_materials` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:299` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:303` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:310` / `prepare_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:463` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:465` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:506` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:539` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:565` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:578` / `finalize_selection` | S | query/ORM | `delete` | ver matriz |
| `backend/app/unified_checkout.py:577` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:164` / `cart_payload` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:540` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:444` / `lock_payment_scope` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:485` / `report_group` | S | query/ORM | `select` | ver matriz |
| `backend/app/unified_checkout.py:542` / `finalize_selection` | S | query/ORM | `select` | ver matriz |
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
| `backend/app/worker.py:104` / `payment_notification_message` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:105` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:139` / `materialize_payment_delivery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:140` / `materialize_payment_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:145` / `materialize_payment_delivery` | X | produtor | `WhatsAppDelivery` | ver matriz |
| `backend/app/worker.py:158` / `materialize_payment_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:170` / `mirror_payment_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:227` / `delivery_message` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:256` / `_record_attempt` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:763` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:106` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:107` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:108` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:109` / `payment_notification_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:192` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:241` / `delivery_message` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:257` / `_record_attempt` | X | produtor | `WhatsAppDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:286` / `process_next_media_job` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:308` / `process_next_media_job` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:309` / `process_next_media_job` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:387` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:410` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:425` / `process_next_whatsapp_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:444` / `process_next_whatsapp_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:530` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:531` / `validate_email_origin` | X | query/ORM | `{'password_recovery': 'password_reset', 'email_verification': 'verify_admin_email'}.get` | ver matriz |
| `backend/app/worker.py:559` / `process_next_email_delivery` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:577` / `process_next_email_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:587` / `process_next_email_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:603` / `process_next_email_delivery` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:688` / `materialize_next_payment_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:701` / `materialize_next_payment_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:766` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:768` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:777` / `process_next_gallery_reopening_notification` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:812` / `reconcile_next_unknown_delivery` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:824` / `reconcile_next_unknown_delivery` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:846` / `run_cycle` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:889` / `process_asset_file_cleanup` | X | query/ORM | `db.scalar` | ver matriz |
| `backend/app/worker.py:951` / `process_admin_security_cleanup` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:197` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:201` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:205` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:274` / `process_next_media_job` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:457` / `process_next_whatsapp_delivery` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:460` / `process_next_whatsapp_delivery` | X | gate | `require_active_owner` | ver matriz |
| `backend/app/worker.py:461` / `process_next_whatsapp_delivery` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:532` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:617` / `process_next_email_delivery` | X | efeito potencial | `decrypt_sensitive_payload` | ver matriz |
| `backend/app/worker.py:623` / `process_next_email_delivery` | X | efeito potencial | `active_provider.send` | ver matriz |
| `backend/app/worker.py:635` / `process_next_email_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:737` / `send` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:745` / `send` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:751` / `send` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:764` / `reopening_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:788` / `process_next_gallery_reopening_notification` | X | gate | `provider_for` | ver matriz |
| `backend/app/worker.py:794` / `process_next_gallery_reopening_notification` | X | efeito potencial | `provider.send_transactional` | ver matriz |
| `backend/app/worker.py:929` / `process_otp_privacy_cleanup` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:954` / `process_admin_security_cleanup` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:141` / `materialize_payment_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:170` / `mirror_payment_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:211` / `validate_otp_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:217` / `validate_otp_origin` | X | gate | `owned_record` | ver matriz |
| `backend/app/worker.py:234` / `delivery_message` | X | efeito potencial | `decrypt_otp` | ver matriz |
| `backend/app/worker.py:322` / `process_next_media_job` | X | query/ORM | `db.scalars` | ver matriz |
| `backend/app/worker.py:328` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:330` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:332` / `process_next_media_job` | X | query/ORM | `derivatives.get` | ver matriz |
| `backend/app/worker.py:486` / `process_next_whatsapp_delivery` | X | query/ORM | `db.execute` | ver matriz |
| `backend/app/worker.py:540` / `validate_email_origin` | X | query/ORM | `db.get` | ver matriz |
| `backend/app/worker.py:636` / `process_next_email_delivery` | X | produtor | `EmailDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:674` / `process_next_email_delivery` | X | query/ORM | `db.add` | ver matriz |
| `backend/app/worker.py:957` / `process_admin_security_cleanup` | X | gate | `domain_session` | ver matriz |
| `backend/app/worker.py:444` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:560` / `process_next_email_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:675` / `process_next_email_delivery` | X | produtor | `EmailDeliveryAttempt` | ver matriz |
| `backend/app/worker.py:702` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:234` / `delivery_message` | X | efeito potencial | `otp_encryption_key` | ver matriz |
| `backend/app/worker.py:929` / `process_otp_privacy_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:954` / `process_admin_security_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:212` / `validate_otp_origin` | X | gate | `require_admin_tenant` | ver matriz |
| `backend/app/worker.py:323` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:388` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:426` / `process_next_whatsapp_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:486` / `process_next_whatsapp_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:546` / `validate_email_origin` | X | query/ORM | `payload.get` | ver matriz |
| `backend/app/worker.py:588` / `process_next_email_delivery` | X | query/ORM | `update` | ver matriz |
| `backend/app/worker.py:578` / `process_next_email_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:411` / `process_next_whatsapp_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:689` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:777` / `process_next_gallery_reopening_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:813` / `reconcile_next_unknown_delivery` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:274` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:290` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:691` / `materialize_next_payment_notification` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:889` / `process_asset_file_cleanup` | X | query/ORM | `select` | ver matriz |
| `backend/app/worker.py:287` / `process_next_media_job` | X | query/ORM | `select` | ver matriz |
| `scripts/assert_homolog_schema_head.py:30` / `migration_heads` | T | query/ORM | `values.get` | ver matriz |
| `scripts/assert_homolog_schema_head.py:35` / `migration_heads` | T | query/ORM | `values.get` | ver matriz |
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
| `scripts/preserve_branding.py:178` / `preserve` | T | query/ORM | `settings.get` | ver matriz |
| `scripts/preserve_branding.py:126` / `extract_asset` | T | efeito potencial | `tarfile.open` | ver matriz |
| `scripts/preserve_branding.py:150` / `receive_backup` | T | efeito potencial | `(backup / 'manifest.json').write_text` | ver matriz |
| `scripts/preserve_branding.py:196` / `preserve` | T | query/ORM | `volume_info.get` | ver matriz |
| `scripts/preserve_branding.py:199` / `preserve` | T | query/ORM | `volume_info.get` | ver matriz |
| `scripts/preserve_branding.py:229` / `preserve` | T | efeito potencial | `(backup / 'manifest.json').write_text` | ver matriz |
| `scripts/preserve_branding.py:92` / `transfer` | T | efeito potencial | `Path(temporary).unlink` | ver matriz |
| `scripts/preserve_branding.py:117` / `container` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:117` / `container` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:149` / `receive_backup` | T | efeito potencial | `(backup / key).write_bytes` | ver matriz |
| `scripts/preserve_branding.py:197` / `preserve` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:197` / `preserve` | T | query/ORM | `labels.get` | ver matriz |
| `scripts/preserve_branding.py:199` / `preserve` | T | query/ORM | `volume_info.get` | ver matriz |
| `scripts/preserve_branding.py:226` / `preserve` | T | efeito potencial | `(backup / key).open` | ver matriz |
| `scripts/preserve_branding.py:238` / `preserve` | T | efeito potencial | `override.open` | ver matriz |
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
| `backend/app/facial/face_worker.py:137` | F | armazenamento/cache/wake-up |
| `backend/app/facial/face_worker.py:138` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:1` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:59` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:361` | F | armazenamento/cache/wake-up |
| `backend/app/facial/jobs.py:374` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:109` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:111` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:134` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:136` | F | armazenamento/cache/wake-up |
| `backend/app/facial/model_assets.py:159` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:21` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:69` | F | armazenamento/cache/wake-up |
| `backend/app/facial/runtime.py:74` | F | armazenamento/cache/wake-up |
| `backend/app/installation_operator.py:13` | O | armazenamento/cache/wake-up |
| `backend/app/main.py:419` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1055` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:1311` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2362` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2506` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2511` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2580` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2590` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:2591` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6034` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6076` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6144` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:6168` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:9146` | X | armazenamento/cache/wake-up |
| `backend/app/main.py:11076` | X | armazenamento/cache/wake-up |
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
| `scripts/deploy-homolog.sh:572` | T | armazenamento/cache/wake-up |
| `scripts/deploy-homolog.sh:574` | T | armazenamento/cache/wake-up |
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
| `scripts/resume-homolog.sh:156` | T | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:44` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:77` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:127` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-diagnostics.tsx:135` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-report.ts:57` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/capacity-report.ts:117` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:75` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:310` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/client-gallery-card.tsx:335` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:25` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:46` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:176` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/folder-processing-panel.tsx:184` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:15` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:24` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:38` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:140` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/preview-adjustment-panel.tsx:170` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:98` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:322` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:335` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:784` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx:826` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/installation-diagnostics.tsx:27` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/notifications/page.tsx:64` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/page.tsx:327` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:77` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:126` | U | armazenamento/cache/wake-up |
| `frontend/app/admin/settings/whatsapp-panel.tsx:219` | U | armazenamento/cache/wake-up |
| `frontend/app/auth-entry.tsx:72` | U | armazenamento/cache/wake-up |
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
| `frontend/app/library/cart/page.tsx:35` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:40` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:68` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:74` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:75` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchase-card.tsx:76` | U | armazenamento/cache/wake-up |
| `frontend/app/library/purchases/page.tsx:22` | U | armazenamento/cache/wake-up |
| `frontend/app/public-galleries/[galleryId]/page.tsx:81` | U | armazenamento/cache/wake-up |
| `frontend/app/push-control.tsx:9` | U | armazenamento/cache/wake-up |
| `frontend/app/push-control.tsx:21` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:12` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:19` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:38` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:49` | U | armazenamento/cache/wake-up |
| `frontend/app/push-device.ts:66` | U | armazenamento/cache/wake-up |
| `frontend/app/theme-control.tsx:29` | U | armazenamento/cache/wake-up |
| `frontend/app/theme.ts:9` | U | armazenamento/cache/wake-up |
| `frontend/app/theme.ts:23` | U | armazenamento/cache/wake-up |
| `frontend/app/upload-jpeg.ts:19` | U | armazenamento/cache/wake-up |
| `frontend/public/markina-sw.js:1` | U | armazenamento/cache/wake-up |
| `frontend/public/markina-sw.js:53` | U | armazenamento/cache/wake-up |
