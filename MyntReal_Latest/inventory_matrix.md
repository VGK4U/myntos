# Legacy Application Inventory Matrix

| File | Portal | Detected Endpoints |
|---|---|---|
| vgk_member_announcements.html | Member | /api/v1/vgk-member/announcements/create?audience=vgk4u |
| vgk_member_awards.html | Member | /api/v1/awards/my-awards?audience=${AUD()} |
| vgk_member_bank_details.html | Member | /api/v1/vgk-member/bank/submit?audience=vgk4u<br>/api/v1/vgk-member/bank/my-details?audience=vgk4u |
| vgk_member_birthdays.html | Member | None detected |
| vgk_member_coupon_activate.html | Member | /api/v1/vgk-member/coupons/activate?audience=vgk4u |
| vgk_member_coupon_benefits.html | Member | /api/v1/vgk/coupon-ledger?audience=${AUD()} |
| vgk_member_coupon_progress.html | Member | /api/v1/vgk-member/coupons/progress?audience=vgk4u |
| vgk_member_coupon_transfer.html | Member | /api/v1/vgk-member/coupons/transfer?audience=vgk4u |
| vgk_member_daywise_income.html | Member | /api/v1/income/daywise?audience=${AUD()}&days=30 |
| vgk_member_direct_summary.html | Member | /api/v1/income/level/1?audience=${AUD()} |
| vgk_member_ev_benefits.html | Member | /api/v1/ev/benefits?audience=${AUD()} |
| vgk_member_ev_discount.html | Member | /api/v1/ev-discount/my-coupons?audience=${AUD()} |
| vgk_member_feedback.html | Member | /api/v1/vgk-member/feedback/my-submissions?audience=vgk4u<br>/api/v1/vgk-member/feedback/submit?audience=vgk4u |
| vgk_member_franchise_earnings.html | Member | /api/v1/franchise/earnings?audience=${AUD()} |
| vgk_member_guru_summary.html | Member | /api/v1/income/level/3?audience=${AUD()} |
| vgk_member_income_types.html | Member | /api/v1/income/summary?audience=${AUD()} |
| vgk_member_insurance.html | Member | /api/v1/insurance/earnings?audience=${AUD()} |
| vgk_member_kyc.html | Member | /api/v1/vgk-member/kyc/upload?audience=vgk4u<br>/api/v1/vgk-member/kyc/my-documents?audience=vgk4u |
| vgk_member_matching_summary.html | Member | /api/v1/income/level/2?audience=${AUD()} |
| vgk_member_my_announcements.html | Member | None detected |
| vgk_member_my_submissions.html | Member | /api/v1/vgk/my-submissions?audience=${AUD()} |
| vgk_member_offers.html | Member | /api/v1/bonanza/vgk/public/active-bonanzas<br>/api/v1/vgk/auth/me<br>/api/v1/vgk/public/commission-rates<br>/api/v1/vgk/media/video-overlay?<br>/api/v1/vgk/public/member-lookup?q=<br>/api/v1/feedback/public/categories<br>/api/v1/feedback/public/announcements?limit=50&platform=vgk |
| vgk_member_offers_telugu.html | Member | /api/v1/vgk/public/commission-rates |
| vgk_member_profile_edit.html | Member | /api/v1/vgk-member/profile/edit?audience=vgk4u |
| vgk_member_settings.html | Member | /api/v1/vgk-member/settings?audience=vgk4u |
| vgk_member_top_earners.html | Member | /api/v1/banners/top-performers?audience=${AUD()} |
| vgk_member_training.html | Member | /api/v1/training/my-courses?audience=${AUD()} |
| vgk_member_ved_summary.html | Member | /api/v1/income/level/4?audience=${AUD()} |
| architecture_view.html | Public/Other | None detected |
| b2b_signup.html | Public/Other | /api/v1/platform-b2b/signup |
| catalog.html | Public/Other | /api/v1/catalog/public/hit<br>/api/v1/catalog/public/referrer?ref= |
| community_landing.html | Public/Other | /api/v1/community-services/public/register<br>/api/v1/community-services/public/active-headers<br>/api/v1/vgk/members/search?q=${encodeURIComponent(query)}<br>/api/v1/community-services/public/services/${shortName} |
| contact.html | Public/Other | /api/v1/promo/track<br>/api/v1/crm/leads/public?company_id=${cid} |
| dashboard.html | Public/Other | None detected |
| docs_access.html | Public/Other | None detected |
| finance_admin_pins.html | Public/Other | None detected |
| finance_awards_payment_processing.html | Public/Other | /api/v1/awards/finance/awards/${type}/${id}/process<br>/api/v1/awards/finance/awards/pending<br>/api/v1/awards/finance/awards/handling-charges-tracker<br>/api/v1/awards/finance/bonanza/${claimId}/tracking |
| finance_awards_payment_v2.html | Public/Other | /api/v1/awards/finance/awards/${type}/${id}/process<br>/api/v1/awards/finance/awards/pending<br>/api/v1/awards/finance/awards/handling-charges-tracker<br>/api/v1/awards/finance/bonanza/${claimId}/tracking |
| finance_compliance.html | Public/Other | None detected |
| finance_cost_analysis.html | Public/Other | None detected |
| finance_tds_management.html | Public/Other | None detected |
| lead-share.html | Public/Other | /api/v1/crm/share/${token}<br>/api/v1/crm/share/${_shareToken}/bundle |
| lead-status-share.html | Public/Other | /api/v1/crm/leads/status-view/${encodeURIComponent(token)} |
| marketplace.html | Public/Other | /api/v1/marketplace/validate-vgk?vgk_code=${encodeURIComponent(code)}&company_id=${COMPANY_ID}<br>/api/v1/crm/leads/public?company_id=${_rdEnqCid}<br>/api/v1/marketplace/filters?<br>/api/v1/marketplace/products?<br>/api/v1/marketplace/pos/<br>/api/v1/marketplace/categories?<br>/api/v1/marketplace/products/<br>/api/v1/marketplace/validate-dealer?dealer_code=${encodeURIComponent(val)}&company_id=${COMPANY_ID}${segParam}<br>/api/v1/auth/me<br>/api/v1/marketplace/segments?company_id=${COMPANY_ID}<br>/api/v1/marketplace/validate-student?student_id=${encodeURIComponent(val)}&company_id=${COMPANY_ID}${segParam}<br>/api/v1/marketplace/validate-mnr?mnr_id=${encodeURIComponent(val)}<br>/api/v1/marketplace/validate-vgk?vgk_code=${encodeURIComponent(val)} |
| mnr_guide.html | Public/Other | /api/v1/mnr/guide/pages |
| mnr_my_commissions.html | Public/Other | None detected |
| mnr_user_guide.html | Public/Other | /api/v1/auth/me-hybrid<br>/api/v1/auth/login<br>/api/v1/mnr/user-guide/pages |
| mnr_validation.html | Public/Other | None detected |
| order_fulfillment_dashboard.html | Public/Other | None detected |
| privacy-policy.html | Public/Other | None detected |
| promo_dashboard.html | Public/Other | /api/v1/promo/my/marketplace-products?influencer_id=${influencer.id}<br>/api/v1/promo/my/change-password?influencer_id=${influencer.id}<br>/api/v1/promo/cross-auth/generate-promo-to-vgk<br>/api/v1/promo/my/profile?influencer_id=${influencer.id}<br>/api/v1/promo/nda/accept?influencer_id=${inf.id}&promo_token=${encodeURIComponent(token)}<br>/api/v1/promo/my/stats?influencer_id=${influencer.id}<br>/api/v1/promo/nda/active?influencer_id=${inf.id}&promo_token=${encodeURIComponent(token)}<br>/api/v1/promo/nda/my-status?influencer_id=${inf.id}&promo_token=${encodeURIComponent(token)}<br>/api/v1/promo/cross-auth/auto-link-vgk<br>/api/v1/promo/my/referral-members?influencer_id=${influencer.id}<br>/api/v1/promo/my/deals?influencer_id=${influencer.id} |
| promo_login.html | Public/Other | /api/v1/promo/cross-auth/redeem-to-promo<br>/api/v1/promo/self-register<br>/api/v1/promo/login<br>/api/v1/password-reset/portal/influencer/reset-password<br>/api/v1/password-reset/portal/influencer/verify-otp<br>/api/v1/password-reset/portal/influencer/forgot-password |
| public_announcement.html | Public/Other | /api/v1/feedback/public/announcement/${id}?track_share=${trackShare}&track_view=${trackView}<br>/api/v1/engagement/public/announcement/${announcementId}/ratings?company_id=1 |
| public_partner.html | Public/Other | /api/v1/hub/partners/<br>/api/v1/social-links/hub |
| public_service_ticket.html | Public/Other | /api/v1/marketplace/public/validate-discount-id?id=${encodeURIComponent(val)}<br>/api/v1/marketplace/public/catalog-search?${params}<br>/api/v1/tickets/service/public/create |
| public_ticket_status.html | Public/Other | /api/v1/tickets/service/public/status/${encodeURIComponent(ticketId)}?phone=${encodeURIComponent(phone)} |
| real_dreams_compare.html | Public/Other | None detected |
| real_dreams_marketplace.html | Public/Other | None detected |
| real_dreams_property_detail.html | Public/Other | /api/v1/crm/leads/public?company_id=${companyId} |
| solar.html | Public/Other | /api/v1/crm/leads/public?company_id=${cid} |
| super_admin_awards_approval.html | Public/Other | None detected |
| team_leads.html | Public/Other | None detected |
| test_categories.html | Public/Other | /api/v1/feedback/categories |
| test_landing.html | Public/Other | None detected |
| test_login.html | Public/Other | /api/v1/staff/sandbox/auth/login |
| test_partner_login.html | Public/Other | /api/v1/staff/sandbox/auth/login |
| test_staff_login.html | Public/Other | /api/v1/staff/sandbox/auth/login |
| user_announcements.html | Public/Other | /api/v1/feedback/announcements/${announcementId}/rate?rating=${rating} |
| user_change_password.html | Public/Other | /api/v1/auth/change-password |
| user_coupon_benefits.html | Public/Other | /api/v1/users/me/points-summary |
| user_daywise_income.html | Public/Other | None detected |
| user_direct_referral.html | Public/Other | /api/v1/financial-operations/income/${window.currentUserId ||  |
| user_earnings.html | Public/Other | /api/v1/myntreal/points/my-history<br>/api/v1/auth/me-hybrid?role=mnr<br>/api/v1/myntreal/earnings-summary<br>/api/v1/myntreal/my-incentives<br>/api/v1/myntreal/points/me |
| user_ev_benefits.html | Public/Other | None detected |
| user_ev_discount.html | Public/Other | None detected |
| user_feedback_submit.html | Public/Other | /api/v1/feedback/media/${mediaRecord.media_id}/thumbnail<br>/api/v1/feedback/categories |
| user_franchise_earnings.html | Public/Other | /api/v1/leads/my-leads?category=franchise |
| user_guru_dakshina.html | Public/Other | /api/v1/financial-operations/income/${window.currentUserId ||  |
| user_matching_referral.html | Public/Other | /api/v1/financial-operations/income/${window.currentUserId ||  |
| user_my_announcements.html | Public/Other | None detected |
| user_my_announcements_approved.html | Public/Other | None detected |
| user_my_announcements_pending.html | Public/Other | None detected |
| user_my_announcements_rejected.html | Public/Other | None detected |
| user_my_leads.html | Public/Other | /api/v1/crm/my-deals<br>/api/v1/auth/me-hybrid?role=mnr<br>/api/v1/crm/unified-my-leads/${leadId}/details?company_id=${companyId}&role=mnr<br>/api/v1/crm/unified-my-leads?${params}<br>/api/v1/crm/unified-my-leads/search-partner?q=${encodeURIComponent(query)}<br>/api/v1/crm/network-search?q=${encodeURIComponent(query)}&limit=10<br>/api/v1/crm/unified-my-leads?role=mnr<br>/api/v1/crm/unified-my-leads/${leadId}/mnr-assignment?role=mnr<br>/api/v1/crm/unified-my-leads/upline/${mnrId}<br>/api/v1/staff/accounts/companies<br>/api/v1/crm/unified-my-leads/claim/${leadId}?role=mnr<br>/api/v1/crm/unified-my-leads/search-staff?q=${encodeURIComponent(query)}<br>/api/v1/crm/unified-my-leads/search-mnr?q=${encodeURIComponent(query)}<br>/api/v1/community-services/admin/active-search?q=${encodeURIComponent(query)}<br>/api/v1/crm/unified-my-leads?segment=assigned&per_page=1&role=mnr<br>/api/v1/crm/unified-my-leads?segment=fresh&per_page=1&role=mnr<br>/api/v1/crm/unified-my-leads?segment=my&per_page=1&role=mnr |
| user_my_submissions.html | Public/Other | /api/v1/feedback/${submissionId} |
| user_points_utilisation.html | Public/Other | /api/v1/myntreal/points/me/history?per_page=50<br>/api/v1/users/me<br>/api/v1/incentives/zynova/real-estate/me<br>/api/v1/receipt/membership-receipt<br>/api/v1/myntreal/points/me |
| user_tickets.html | Public/Other | None detected |
| user_vgk4u_insurance.html | Public/Other | /api/v1/myntreal/zynova/insurance/team<br>/api/v1/users/zynova/insurance |
| user_vgk4u_my_leads.html | Public/Other | /api/v1/crm/unified-my-leads/<br>/api/v1/vgk/dashboard/profile<br>/api/v1/vgk/dashboard/leads/${leadId}/set-support<br>/api/v1/vgk/dashboard/leads? |
| user_vgk4u_real_estate.html | Public/Other | /api/v1/myntreal/zynova/real-estate/team<br>/api/v1/users/zynova/real-estate |
| user_vgk4u_training.html | Public/Other | /api/v1/myntreal/zynova/training/me |
| user_withdrawals.html | Public/Other | /api/v1/withdrawals/income-transactions?${params}<br>/api/v1/auth/me |
| vgk_awards_oversight.html | Public/Other | None detected |
| vgk_awards_procurement.html | Public/Other | /api/v1/staff/points-insurance/insurance/eligible-users?limit=${pageSize}&offset=${offset}<br>/api/v1/awards/finance/awards/${awardType}/${awardId}/process |
| vgk_bonanza_claims.html | Public/Other | None detected |
| vgk_bonanza_management.html | Public/Other | None detected |
| vgk_cash_income_accounts.html | Public/Other | None detected |
| vgk_cash_income_sales.html | Public/Other | None detected |
| vgk_categories.html | Public/Other | None detected |
| vgk_company_earnings.html | Public/Other | None detected |
| vgk_company_earnings_landing.html | Public/Other | None detected |
| vgk_compliance.html | Public/Other | None detected |
| vgk_dashboard.html | Public/Other | /api/v1/vgk/member-card-preview/<br>/api/v1/bonanza/my-reward-files<br>/api/v1/vgk/dashboard/leads/<br>/api/v1/promo/cross-auth/generate-vgk-to-partner<br>/api/v1/vgk/public/member-lookup?q=<br>/api/v1/vgk/dashboard/member-network/${encodeURIComponent(partnerCode)}<br>/api/v1/bonanza/my-bonanzas<br>/api/v1/bonanza/<br>/api/v1/vgk/media/video-overlay?${params}<br>/api/v1/crm/unified-my-leads/<br>/api/v1/vgk/member/accept-terms<br>/api/v1/bonanza/claim/<br>/api/v1/promo/cross-auth/check-promo-link?partner_code=<br>/api/v1/promo/cross-auth/generate-vgk-to-promo<br>/api/v1/vgk/vendor/directory/categories<br>/api/v1/vgk/vendor/directory?${params}<br>/api/v1/vgk/auth/is-card-admin<br>/api/v1/feedback/public/announcements?platform=vgk&limit=20<br>/api/v1/vgk/member/redeem-promo<br>/api/v1/vgk/member-card-preview/me<br>/api/v1/vgk/auth/me<br>/api/v1/banners/birthday-today<br>/api/v1/banners/top-performers?audience=vgk4u&limit=5<br>/api/v1/community-services/my-earnings<br>/api/v1/promo/cross-auth/check-partner-link?partner_code= |
| vgk_dc_shadow_mode.html | Public/Other | None detected |
| vgk_expenses_management.html | Public/Other | None detected |
| vgk_expense_details.html | Public/Other | None detected |
| vgk_finance_supreme.html | Public/Other | None detected |
| vgk_history_supreme.html | Public/Other | None detected |
| vgk_income_finance_complete.html | Public/Other | None detected |
| vgk_income_history.html | Public/Other | None detected |
| vgk_income_records.html | Public/Other | None detected |
| vgk_income_supreme.html | Public/Other | None detected |
| vgk_income_unified.html | Public/Other | /api/v1/bonanza/vgk/pending-payments?stage=all<br>/api/v1/bonanza/vgk/claims/${claimId}/status<br>/api/v1/vgk/staff/vgk/cash-income/payment-options<br>/api/v1/vgk/staff/vgk/cash-income/unified-action?company_id=${entryCo}<br>/api/v1/vgk/staff/vgk/field-allowances/${faId}/stage1-approve<br>/api/v1/vgk/staff/vgk/field-allowances/${faId}/stage2-mark-paid<br>/api/v1/vgk/staff/vgk/cash-income/${entryId}/send-whatsapp?company_id=${companyCo}<br>/api/v1/vgk/staff/vgk/field-allowances?${faQp.toString()}<br>/api/v1/vgk/staff/vgk/cash-income/${entryId}/earner-card?company_id=${co}<br>/api/v1/vgk/staff/vgk/cash-income/${entryId}/earner-card?company_id=${companyCo}<br>/api/v1/bonanza/vgk/claims/${CURRENT.claim_id}/status<br>/api/v1/vgk/staff/vgk/cash-income/unified-list?${qp.toString()} |
| vgk_login.html | Public/Other | /api/v1/promo/cross-auth/redeem-to-vgk<br>/api/v1/bonanza/vgk/public/active-bonanzas<br>/api/v1/vgk/auth/me<br>/api/v1/vgk/auth/signup/verify-otp<br>/api/v1/vgk/member/accept-terms<br>/api/v1/vgk/public/influencer-lookup?code=<br>/api/v1/vgk/public/terms<br>/api/v1/vgk/auth/signup/send-otp<br>/api/v1/password-reset/portal/vgk_partner/forgot-password<br>/api/v1/vgk/media/video-overlay?<br>/api/v1/vgk/public/member-lookup?q=<br>/api/v1/vgk/auth/login<br>/api/v1/vgk/public/promo-check?code=<br>/api/v1/password-reset/portal/vgk_partner/reset-password<br>/api/v1/password-reset/portal/vgk_partner/verify-otp<br>/api/v1/vgk/auth/signup |
| vgk_password_change.html | Public/Other | /api/v1/rvz/password/change-password<br>/api/v1/rvz/password/search-users |
| vgk_payout_details.html | Public/Other | None detected |
| vgk_popup_control.html | Public/Other | None detected |
| vgk_revenue_details.html | Public/Other | None detected |
| vgk_sandbox_manager.html | Public/Other | None detected |
| vgk_secondary_password_setup.html | Public/Other | /api/v1/secondary/check-secondary-status<br>/api/v1/secondary/setup-secondary-password |
| vgk_vendor_directory.html | Public/Other | None detected |
| vgk_wallet_withdrawals.html | Public/Other | None detected |
| vgk_withdrawal_supreme.html | Public/Other | None detected |
| _vgk_member_page_template.html | Public/Other | None detected |
| staff_2fa_settings.html | Staff | None detected |
| staff_accounts_bom.html | Staff | None detected |
| staff_accounts_capital.html | Staff | None detected |
| staff_accounts_cash_in_hand.html | Staff | None detected |
| staff_accounts_community_services.html | Staff | /api/v1/community-services/admin/services<br>/api/v1/community-services/admin/services/${id} |
| staff_accounts_companies.html | Staff | None detected |
| staff_accounts_dar.html | Staff | None detected |
| staff_accounts_duties_taxes.html | Staff | None detected |
| staff_accounts_estimations.html | Staff | None detected |
| staff_accounts_expense_categories.html | Staff | None detected |
| staff_accounts_expense_entries.html | Staff | None detected |
| staff_accounts_fund_allocations.html | Staff | None detected |
| staff_accounts_general_ledger.html | Staff | /api/v1/staff/accounts/vendors<br>/api/v1/staff/accounts/party-search/add-manual |
| staff_accounts_hsn.html | Staff | None detected |
| staff_accounts_income_entries.html | Staff | None detected |
| staff_accounts_journal_voucher.html | Staff | /api/v1/staff/accounts/vendors<br>/api/v1/staff/accounts/party-search/add-manual |
| staff_accounts_ledger_masters.html | Staff | None detected |
| staff_accounts_manufacturing.html | Staff | None detected |
| staff_accounts_parties_master.html | Staff | None detected |
| staff_accounts_party_ledger.html | Staff | None detected |
| staff_accounts_payables.html | Staff | None detected |
| staff_accounts_pending_clear.html | Staff | None detected |
| staff_accounts_pricing.html | Staff | None detected |
| staff_accounts_procurement.html | Staff | /api/v1/staff/accounts/procurement/spare-orders/${orderId}/receipt/${vendorId}<br>/api/v1/staff/accounts/procurement/spare-orders/${_spoModalOrderId}/approve<br>/api/v1/staff/accounts/procurement/spare-orders/${orderId}/purchase-prefill/${vendorId}<br>/api/v1/staff/accounts/procurement/spare-orders/${_spoModalOrderId}/review-update<br>/api/v1/staff/accounts/vendors?search=${encodeURIComponent(query)}&page_size=8<br>/api/v1/staff/accounts/procurement/spare-orders/${orderId}/send-whatsapp/${vendorId}<br>/api/v1/staff/accounts/procurement/spare-items/${itemId}/vendors<br>/api/v1/staff/accounts/procurement/spare-orders/${orderId}<br>/api/v1/staff/accounts/procurement/spare-orders/${spareDraftOrderId}/submit<br>/api/v1/staff/accounts/procurement/spare-orders/${orderId}/cancel<br>/api/v1/staff/accounts/procurement/spare-orders<br>/api/v1/staff/accounts/procurement/spare-vendors/${vendor.vendor_id}/items?exclude_ids=${excIds}${co ? <br>/api/v1/partner/orders/stock-short?${params} |
| staff_accounts_purchase_invoices.html | Staff | None detected |
| staff_accounts_receivables.html | Staff | None detected |
| staff_accounts_reports.html | Staff | None detected |
| staff_accounts_sales_invoices.html | Staff | /api/v1/staff/accounts/sales-coupons<br>/api/v1/staff/accounts/stock-items?is_active=true&page_size=2000&include_summary=false${cacheParam}<br>/api/v1/staff/accounts/sales-invoices/${invoiceId}/toggle-dispatch-tracking<br>/api/v1/staff/accounts/party-search?q=${encodeURIComponent(q.trim())}&limit=25<br>/api/v1/staff/accounts/sales-invoices/${currentInvoiceId}/apply-coupon<br>/api/v1/staff/accounts/sales-invoices/${invoiceId}?company_id=${companyId}<br>/api/v1/staff/accounts/companies<br>/api/v1/staff/accounts/sales-invoices/${currentInvoiceId}/coupon?company_id=${companyId}<br>/api/v1/staff/accounts/sales-invoices/${currentInvoiceId}/manual-discount<br>/api/v1/staff/accounts/hsn<br>/api/v1/staff/accounts/sales-invoices/${currentInvoiceId}/line-items<br>/api/v1/staff/accounts/sales-invoices/billing-companies<br>/api/v1/marketplace/catalog-search?limit=500<br>/api/v1/staff/accounts/sales-invoices/${invoiceId}/payments<br>/api/v1/staff/accounts/sales-invoices/${id}<br>/api/v1/staff/accounts/sales-invoices/${id}/cancel<br>/api/v1/staff/accounts/sales-invoices/${id}/confirm<br>/api/v1/staff/accounts/sales-invoices/${invId}/payments?company_id=${companyId}<br>/api/v1/staff/accounts/sales-invoices/${invoiceId}/payments?company_id=${companyId}<br>/api/v1/staff/accounts/sales-invoices/${invId}?company_id=${companyId}<br>/api/v1/staff/accounts/sales-invoices/${invId}/payments<br>/api/v1/staff/accounts/sales-invoices/${currentInvoiceId}/billing-company<br>/api/v1/staff/accounts/sales-coupons/${couponId}<br>/api/v1/staff/auth/me<br>/api/v1/staff/accounts/sales-invoices/${currentInvoiceId}/document-type |
| staff_accounts_segments.html | Staff | None detected |
| staff_accounts_stock_items.html | Staff | /api/v1/staff/accounts/stock-items/${itemId}/marketplace-link<br>/api/v1/staff/accounts/stock-items/${itemId}/images/${imageId}/primary<br>/api/v1/staff/accounts/stock-items/${itemId}/images/${imageId}<br>/api/v1/staff/accounts/stock-items/${itemId}/image-link<br>/api/v1/marketplace/sync/logs?company_id=${companyId}&limit=1<br>/api/v1/staff/accounts/stock-items/${itemId}/images<br>/api/v1/marketplace/sync/status?company_id=${companyId}<br>/api/v1/marketplace/sync?company_id=${companyId} |
| staff_accounts_vendors.html | Staff | None detected |
| staff_ai_calling.html | Staff | None detected |
| staff_ai_marketing_pro.html | Staff | None detected |
| staff_ai_segments.html | Staff | None detected |
| staff_all_journeys.html | Staff | None detected |
| staff_attendance_computation.html | Staff | None detected |
| staff_attendance_exceptions.html | Staff | /api/v1/staff/attendance-sheet/exceptions/summary?${params.toString()}<br>/api/v1/staff/departments |
| staff_attendance_reports.html | Staff | None detected |
| staff_attendance_sheet.html | Staff | None detected |
| staff_audit_logs.html | Staff | None detected |
| staff_b2b_clients.html | Staff | None detected |
| staff_bank_wise_leads.html | Staff | None detected |
| staff_call_management.html | Staff | /api/v1/crm/dialer/analytics?period=${period} |
| staff_call_quality.html | Staff | None detected |
| staff_change_password.html | Staff | None detected |
| staff_configuration_a1top.html | Staff | None detected |
| staff_configuration_razorpay.html | Staff | None detected |
| staff_consolidated.html | Staff | /api/v1/staff/accounts/companies?page_size=50 |
| staff_coupon_status.html | Staff | None detected |
| staff_crm_dashboard.html | Staff | None detected |
| staff_crm_dashboard_backup.html | Staff | None detected |
| staff_crm_team_leads.html | Staff | None detected |
| staff_crm_whatsapp_inbox.html | Staff | None detected |
| staff_dashboard.html | Staff | None detected |
| staff_day_planner.html | Staff | None detected |
| staff_day_planner_guide.html | Staff | /api/v1/staff/guide/pages<br>/api/v1/staff/platform-setup-guide |
| staff_day_planner_manager.html | Staff | None detected |
| staff_departments.html | Staff | None detected |
| staff_dialer.html | Staff | /api/v1 |
| staff_employees.html | Staff | None detected |
| staff_employee_directory.html | Staff | None detected |
| staff_etc_students.html | Staff | None detected |
| staff_executive_dashboard.html | Staff | None detected |
| staff_hr_candidates.html | Staff | None detected |
| staff_hr_job_postings.html | Staff | None detected |
| staff_incentives_approvals.html | Staff | None detected |
| staff_incentives_points.html | Staff | /api/v1/myntreal/points/initialize/${userId.toUpperCase()}<br>/api/v1/myntreal/points/${userId}/history<br>/api/v1/receipt/membership-receipt/<br>/api/v1/staff/points-insurance/insurance/issue<br>/api/v1/myntreal/points/backfill-receipts<br>/api/v1/staff/points-insurance/adjust-points<br>/api/v1/myntreal/points/initialize-all |
| staff_incentives_vgk4u.html | Staff | /api/v1/myntreal/zynova/members/${memberId}/status<br>/api/v1/myntreal/zynova/members/hierarchy<br>/api/v1/myntreal/zynova/members/${memberId}/promote<br>/api/v1/myntreal/zynova/members<br>/api/v1/myntreal/zynova/members/${memberId} |
| staff_incentive_source.html | Staff | None detected |
| staff_income_trigger.html | Staff | /api/v1/rvz/scheduler/ved-tracker/${userId} |
| staff_inventory_accessories.html | Staff | None detected |
| staff_inventory_color_sheet.html | Staff | None detected |
| staff_inventory_intake.html | Staff | None detected |
| staff_inventory_stock_ledger.html | Staff | None detected |
| staff_inventory_stock_transfers.html | Staff | None detected |
| staff_inventory_stock_validation.html | Staff | /api/v1/staff/auth/me |
| staff_kra_review.html | Staff | None detected |
| staff_kra_status.html | Staff | None detected |
| staff_kra_templates.html | Staff | None detected |
| staff_kra_tracking_sheet.html | Staff | None detected |
| staff_kyc_approvals.html | Staff | None detected |
| staff_leads.html | Staff | /api/v1/crm/unified-my-leads/search-partner?q=${encodeURIComponent(q)}<br>/api/v1/community-services/admin/active-search?q=${encodeURIComponent(query)}<br>/api/v1/crm/network-search?q=${encodeURIComponent(query)}&limit=10 |
| staff_lead_category.html | Staff | None detected |
| staff_lead_sources.html | Staff | /api/v1/crm/sources/${deleteSourceId}?company_id=${currentCompanyId} |
| staff_lead_sync.html | Staff | /api/v1/crm/lead-sync/admin/cleanup-duplicates?dry_run=<br>/api/v1/crm/lead-sync/admin/cleanup-duplicates?dry_run=true<br>/api/v1/crm/lead-sync/configs/<br>/api/v1/crm/lead-sync/configs<br>/api/v1/crm/lead-sync/run/<br>/api/v1/crm/lead-sync/preview/ |
| staff_leave_approvals.html | Staff | None detected |
| staff_login.html | Staff | /api/v1/password-reset/portal/staff/verify-otp<br>/api/v1/feedback/public/announcements?limit=10<br>/api/v1/password-reset/portal/staff/forgot-password<br>/api/v1/staff/auth/me<br>/api/v1/password-reset/portal/staff/reset-password |
| staff_marketplace_codes_segments.html | Staff | None detected |
| staff_marketplace_config.html | Staff | /api/v1/marketplace/admin/products/${id}/image?company_id=${COMPANY_ID}<br>/api/v1/marketplace/products/${id}/toggle?company_id=${COMPANY_ID}<br>/api/v1/marketplace/sync/logs?company_id=${COMPANY_ID}&limit=5<br>/api/v1/marketplace/admin/stock-dashboard?company_id=${COMPANY_ID}<br>/api/v1/marketplace/admin/products/${id}/clear-overrides?company_id=${COMPANY_ID}<br>/api/v1/marketplace/admin/products/${id}?company_id=${COMPANY_ID}<br>/api/v1/auth/me<br>/api/v1/marketplace/config/categories/${encodeURIComponent(categoryName)}?company_id=${COMPANY_ID}<br>/api/v1/marketplace/segments?company_id=${COMPANY_ID}<br>/api/v1/marketplace/admin/products?${params}<br>/api/v1/marketplace/config/categories?company_id=${COMPANY_ID}<br>/api/v1/marketplace/categories?company_id=${COMPANY_ID} |
| staff_meta_ads_center.html | Staff | None detected |
| staff_meta_ai_agent.html | Staff | /api/v1/meta-ads/agent/chat |
| staff_meta_campaigns.html | Staff | None detected |
| staff_meta_creative_studio.html | Staff | None detected |
| staff_meta_leads.html | Staff | None detected |
| staff_meta_settings.html | Staff | None detected |
| staff_mnr_announcements_view.html | Staff | /api/v1/staff/mnr-user/announcements/all?${params}<br>/api/v1/staff/mnr-user/announcements/${announcementId}/media<br>/api/v1/feedback/staff/submit<br>/api/v1/staff/mnr-user/announcements/${announcementId}/media/${mediaId}<br>/api/v1/feedback/${announcementId}/display-order<br>/api/v1/feedback/public/categories<br>/api/v1/staff/mnr-user/announcements/${announcementId}/edit |
| staff_mnr_leads_master.html | Staff | /api/v1/staff/auth/me |
| staff_my_attendance.html | Staff | None detected |
| staff_my_incentives.html | Staff | None detected |
| staff_my_journeys.html | Staff | None detected |
| staff_my_kras.html | Staff | None detected |
| staff_my_kyc.html | Staff | None detected |
| staff_my_leads.html | Staff | /api/v1/crm/unified-my-leads/search-mnr?q=${encodeURIComponent(q)}<br>/api/v1/staff/accounts/companies<br>/api/v1/community-services/admin/active-search?q=${encodeURIComponent(query)}<br>/api/v1/crm/unified-my-leads?role=mnr<br>/api/v1/crm/unified-my-leads?segment=assigned&target_user_id=${currentMemberId}&page=1&per_page=1<br>/api/v1/crm/leads/${leadId}/claim${params}<br>/api/v1/crm/unified-my-leads?segment=my&target_user_id=${currentMemberId}&page=1&per_page=1<br>/api/v1/crm/unified-my-leads/search-partner?q=${encodeURIComponent(query)}<br>/api/v1/crm/unified-my-leads?segment=my&role=mnr&page=1&per_page=1<br>/api/v1/crm/unified-my-leads?segment=fresh&role=mnr&page=1&per_page=1<br>/api/v1/crm/unified-my-leads?segment=team&role=mnr&per_page=1<br>/api/v1/crm/unified-my-leads?segment=my&role=mnr&status=won&page=1&per_page=1<br>/api/v1/crm/unified-my-leads/${leadId}/details?company_id=${companyId}&role=mnr<br>/api/v1/crm/unified-my-leads/search-staff?q=${encodeURIComponent(query)}<br>/api/v1/crm/unified-my-leads?segment=assigned&role=mnr&page=1&per_page=1<br>/api/v1/crm/unified-my-leads/search-mnr?q=a<br>/api/v1/crm/unclaimed-leads?company_id=${cid}<br>/api/v1/crm/unified-my-leads?${params}<br>/api/v1/crm/network-search?q=${encodeURIComponent(query)}&limit=10<br>/api/v1/staff/auth/me<br>/api/v1/crm/unified-my-leads/claim/${leadId}?role=mnr |
| staff_my_leaves.html | Staff | None detected |
| staff_my_location_history.html | Staff | None detected |
| staff_my_reimbursement_claims.html | Staff | None detected |
| staff_my_tenant.html | Staff | /api/v1/platform-b2b |
| staff_my_timesheet.html | Staff | /api/v1/tickets/service/${ticketStrId}/${action} |
| staff_my_vgk_registrations.html | Staff | None detected |
| staff_nda_acceptance_audit.html | Staff | None detected |
| staff_nda_editor.html | Staff | None detected |
| staff_nda_pending.html | Staff | None detected |
| staff_nda_versions.html | Staff | None detected |
| staff_offboarding.html | Staff | None detected |
| staff_operator_calls.html | Staff | None detected |
| staff_page_registry.html | Staff | None detected |
| staff_partner_sales.html | Staff | /api/v1/partner/staff-view/partner-invoices/${id}<br>/api/v1/partner/staff-view/partner-invoices?${params}<br>/api/v1/partner/staff-view/partner-invoices?per_page=1 |
| staff_partner_stock.html | Staff | None detected |
| staff_partner_walkins.html | Staff | /api/v1/partner/staff-view/partner-walkins?${params}<br>/api/v1/partner/staff-view/partner-walkins/${id}<br>/api/v1/partner/staff-view/partner-walkins?per_page=1 |
| staff_performance_config.html | Staff | /api/v1/staff/performance/config/custom/<br>/api/v1/staff/performance/config/custom |
| staff_platform_setup_guide.html | Staff | /api/v1/staff/platform-setup-guide |
| staff_progress.html | Staff | None detected |
| staff_promoters.html | Staff | None detected |
| staff_promo_nda_audit.html | Staff | None detected |
| staff_promo_nda_editor.html | Staff | None detected |
| staff_reimbursement_approval.html | Staff | None detected |
| staff_sales_report.html | Staff | None detected |
| staff_service_center_revenue.html | Staff | /api/v1/tickets/partners |
| staff_service_center_tracking.html | Staff | None detected |
| staff_service_dashboard.html | Staff | /api/v1/tickets/service/showroom-breakdown?${getFilterParams(<br>/api/v1/tickets/service/vendor-repair-tracker<br>/api/v1/tickets/service-centers<br>/api/v1/tickets/service/procurement-queue<br>/api/v1/tickets/service/dashboard-stats?${getFilterParams(<br>/api/v1/staff/employees?status=active&limit=100<br>/api/v1/tickets/service/technician-breakdown?${getFilterParams( |
| staff_service_performance.html | Staff | None detected |
| staff_service_procurement.html | Staff | /api/v1/tickets/service/spares/${spareId}/update<br>/api/v1/tickets/service/spares/${spareId}/cancel<br>/api/v1/tickets/service/procurement-queue<br>/api/v1/tickets/service/spares/${spareId}/release<br>/api/v1/tickets/service/stock-items/search?q=${encodeURIComponent(query)}<br>/api/v1/tickets/service/spares/${spareId}/pricing<br>/api/v1/tickets/service/spares/${spareId}/acknowledge<br>/api/v1/marketplace-po/catalog-search?q=${encodeURIComponent(query)}&limit=10 |
| staff_service_queue.html | Staff | /api/v1/tickets/service/${ticketId}/diagnose<br>/api/v1/tickets/service/spares/${spareId}/availability<br>/api/v1/tickets/service/billing/${billingId}/items/${itemId}<br>/api/v1/tickets/service/billing/${billingId}/items/${itemId}/serial-numbers<br>/api/v1/tickets/service/spares/${_vrtSpareId}/send-to-vendor<br>/api/v1/tickets/service/${ticketId}/billing/create<br>/api/v1/staff/accounts/service-center-tracking/receipts<br>/api/v1/tickets/service/${ticketId}/complete<br>/api/v1/staff/accounts/vendors?page_size=100<br>/api/v1/tickets/service/tickets/${ticketId}/vehicle-serial<br>/api/v1/tickets/partners<br>/api/v1/tickets/${ticketId}/reassign-staff<br>/api/v1/staff/employees?limit=100&status=active<br>/api/v1/marketplace/pos/${po.id}/generate-invoice?company_id=${COMPANY_ID}<br>/api/v1/tickets/service/billing/${billingId}/coupon<br>/api/v1/staff/accounts/stock-items?search=${encodeURIComponent(q)}&page_size=15<br>/api/v1/tickets/service/${_cspTicketId}/customer-spares<br>/api/v1/tickets/service/${ticketId}/billing<br>/api/v1/tickets/service/spares/${spareId}/warranty-toggle<br>/api/v1/tickets/service/${_csr_ticketId}/request-spares<br>/api/v1/tickets/service/billing/${billingId}/add-item<br>/api/v1/marketplace/pos/${poId}?company_id=${COMPANY_ID}<br>/api/v1/tickets/service/spares/${spareId}/payment<br>/api/v1/tickets/service/billing/${billingId}/apply-coupon<br>/api/v1/tickets/service/billing/companies<br>/api/v1/tickets/service/${ticketId}/update-status<br>/api/v1/tickets/service/${ticketId}/billing/auto-populate<br>/api/v1/tickets/service/spares/${spareId}/transactions/${txnId}<br>/api/v1/tickets/service/queue<br>/api/v1/tickets/service/billing/${billingId}/record-payment<br>/api/v1/tickets/service/spares/${spareId}/cancel<br>/api/v1/tickets/service/${ticketId}/acknowledge<br>/api/v1/tickets/service/spares/${spareId}/dispatch<br>/api/v1/tickets/${ticketId}/attachments<br>/api/v1/tickets/service/repair-queue?route=${route}<br>/api/v1/tickets/service/billing/${billingId}/company<br>/api/v1/tickets/service/spares/${spareId}/repair-route<br>/api/v1/tickets/service/billing/${billingId}/pdf?mode=${mode}<br>/api/v1/tickets/service/spares/${spareId}/accept<br>/api/v1/tickets/service/${ticketId}/spare-transactions<br>/api/v1/tickets/service/${ticketId}/close<br>/api/v1/tickets/service/billing/${billingId}/manual-discount<br>/api/v1/marketplace/catalog-search?${params}<br>/api/v1/tickets/service/${ticketId}/spare-requests<br>/api/v1/tickets/service/spares/${_vrtSpareId}/mark-repaired-received |
| staff_service_raise_ticket.html | Staff | /api/v1/tickets/${ticketId}/upload-attachment<br>/api/v1/tickets/service/create<br>/api/v1/tickets/partners?search=${encodeURIComponent(term)}<br>/api/v1/marketplace/public/catalog-search?${params}<br>/api/v1/marketplace/public/validate-discount-id?id=${encodeURIComponent(val)}<br>/api/v1/tickets/partners |
| staff_service_reports.html | Staff | None detected |
| staff_service_ticket_guide.html | Staff | None detected |
| staff_session_guide.html | Staff | /api/v1/staff/progress/summary?target_date=2026-03-01 |
| staff_settings.html | Staff | None detected |
| staff_sidebar_sync.html | Staff | None detected |
| staff_signup_categories.html | Staff | None detected |
| staff_snapshot.html | Staff | None detected |
| staff_solar_vendors.html | Staff | None detected |
| staff_tasks_assigned_by_me.html | Staff | None detected |
| staff_tasks_assigned_to_me.html | Staff | None detected |
| staff_task_review.html | Staff | None detected |
| staff_task_tracker.html | Staff | None detected |
| staff_team_activities.html | Staff | None detected |
| staff_team_attendance.html | Staff | None detected |
| staff_team_attendance_summary.html | Staff | None detected |
| staff_team_journeys.html | Staff | None detected |
| staff_team_leads.html | Staff | /api/v1/staff-accounts/vendors?search=${encodeURIComponent(val)}&page_size=8<br>/api/v1/staff-accounts/vendors?search=${encodeURIComponent(val)}&page_size=10<br>/api/v1/community-services/admin/active-search?q=${encodeURIComponent(query)}<br>/api/v1/crm/unified-my-leads/search-mnr?q=${encodeURIComponent(query)}&limit=10<br>/api/v1/crm/network-search?q=${encodeURIComponent(query)}&limit=12 |
| staff_team_leads_consolidated.html | Staff | None detected |
| staff_team_location_tracker.html | Staff | None detected |
| staff_testing_req.html | Staff | None detected |
| staff_timesheet_approval.html | Staff | None detected |
| staff_training_videos.html | Staff | None detected |
| staff_validation.html | Staff | None detected |
| staff_vendor_returns.html | Staff | /api/v1/tickets/service/${ticketId} |
| staff_vgk4u_insurance.html | Staff | /api/v1/myntreal/zynova/members/hierarchy<br>/api/v1/myntreal/zynova/members/${memberId}<br>/api/v1/myntreal/zynova/members<br>/api/v1/myntreal/zynova/members/${memberId}/promote |
| staff_vgk4u_journeys.html | Staff | None detected |
| staff_vgk4u_po.html | Staff | None detected |
| staff_vgk4u_real_estate.html | Staff | /api/v1/myntreal/zynova/members/hierarchy<br>/api/v1/myntreal/zynova/members/${memberId}<br>/api/v1/myntreal/zynova/members<br>/api/v1/myntreal/zynova/members/${memberId}/promote |
| staff_vgk_config.html | Staff | None detected |
| staff_vgk_coupons.html | Staff | None detected |
| staff_vgk_income.html | Staff | None detected |
| staff_vgk_media.html | Staff | None detected |
| staff_vgk_members.html | Staff | None detected |
| staff_vgk_promo_codes.html | Staff | None detected |
| staff_vgk_vendors.html | Staff | None detected |
| staff_vgk_vendor_categories.html | Staff | None detected |
| staff_vgk_vendor_detail.html | Staff | None detected |
| staff_vgk_vendor_products.html | Staff | None detected |
| staff_vgk_vendor_transactions.html | Staff | None detected |
| staff_website_assets.html | Staff | None detected |
| staff_whatsapp_config.html | Staff | /api/v1/whatsapp-config/templates?limit=200<br>/api/v1/whatsapp-config/credentials<br>/api/v1/whatsapp-config/meta-templates/fetch<br>/api/v1/whatsapp-config/meta-templates/link |
| staff_whatsapp_inbox.html | Staff | None detected |
| staff_whatsapp_monitor.html | Staff | None detected |
| admin_awards.html | Superadmin | None detected |
| admin_awards_all.html | Superadmin | None detected |
| admin_awards_awardwise.html | Superadmin | /api/v1/awards/admin/awards/<br>/api/v1/awards/admin/awards/pending?limit=500 |
| admin_awards_bonanza.html | Superadmin | None detected |
| admin_awards_simple.html | Superadmin | /api/v1/awards/admin/awards/<br>/api/v1/awards/admin/awards/pending?limit=500 |
| admin_awards_userwise.html | Superadmin | /api/v1/awards/admin/awards/<br>/api/v1/awards/admin/awards/pending?limit=500 |
| admin_bank_all.html | Superadmin | None detected |
| admin_bank_pending.html | Superadmin | None detected |
| admin_banners_management.html | Superadmin | None detected |
| admin_birthdays.html | Superadmin | None detected |
| admin_coupons_activate.html | Superadmin | None detected |
| admin_coupons_buy.html | Superadmin | None detected |
| admin_coupons_progress.html | Superadmin | None detected |
| admin_coupons_status.html | Superadmin | None detected |
| admin_coupons_transfer.html | Superadmin | None detected |
| admin_data_recovery.html | Superadmin | /api/v1/rvz/recovery/restore<br>/api/v1/rvz/recovery/deleted-data |
| admin_delete_management.html | Superadmin | /api/v1/bonanza/list?status=Approved<br>/api/v1/bonanza/delete/${deleteItemId} |
| admin_earnings_direct.html | Superadmin | None detected |
| admin_earnings_gurudakshina.html | Superadmin | None detected |
| admin_earnings_matching.html | Superadmin | None detected |
| admin_earnings_summary_new.html | Superadmin | None detected |
| admin_earnings_ved.html | Superadmin | None detected |
| admin_earnings_withdrawals.html | Superadmin | None detected |
| admin_emergency_wallet.html | Superadmin | None detected |
| admin_ev_benefit_analytics.html | Superadmin | None detected |
| admin_feedback_pending.html | Superadmin | /api/v1/feedback/approve/${selectedSubmission.id}<br>/api/v1/feedback/media/reject/${mediaId}<br>/api/v1/feedback/media/approve/${mediaId}<br>/api/v1/feedback/reject/${selectedSubmission.id}<br>/api/v1/feedback/media/replace/${currentEditingMedia.id}<br>/api/v1/feedback/media/reject/${media.id} |
| admin_income_pending.html | Superadmin | None detected |
| admin_income_verified.html | Superadmin | None detected |
| admin_kyc_management.html | Superadmin | None detected |
| admin_members_all.html | Superadmin | None detected |
| admin_members_direct.html | Superadmin | None detected |
| admin_members_picture.html | Superadmin | None detected |
| admin_members_ved.html | Superadmin | None detected |
| admin_password_reset.html | Superadmin | None detected |
| admin_popups.html | Superadmin | None detected |
| admin_reports.html | Superadmin | None detected |
| admin_tickets_assigned.html | Superadmin | None detected |
| admin_tickets_management.html | Superadmin | None detected |
| admin_users.html | Superadmin | None detected |
| admin_user_status.html | Superadmin | None detected |
| admin_vgk_all-benefits.html | Superadmin | None detected |
| admin_vgk_ev-discount-training.html | Superadmin | None detected |
| admin_vgk_fleet-orders.html | Superadmin | None detected |
| admin_vgk_franchise-earnings.html | Superadmin | None detected |
| admin_vgk_insurance-earnings.html | Superadmin | None detected |
| admin_vgk_referral-income.html | Superadmin | None detected |
| admin_view_announcements.html | Superadmin | None detected |
| rvz_banners_management.html | Superadmin | None detected |
| rvz_banners_standalone.html | Superadmin | None detected |
| rvz_crm_leads.html | Superadmin | /api/v1/staff-accounts/vendors?search=${encodeURIComponent(val)}&page_size=10<br>/api/v1/community-services/admin/active-search?q=${encodeURIComponent(query)}<br>/api/v1/staff-accounts/vendors?search=${encodeURIComponent(val)}&page_size=8<br>/api/v1/crm/network-search?q=${encodeURIComponent(query)}&limit=12 |
| rvz_department_management.html | Superadmin | None detected |
| rvz_menu_access_config.html | Superadmin | None detected |
| rvz_real_dreams_banners.html | Superadmin | None detected |
| rvz_real_dreams_dashboard.html | Superadmin | None detected |
| rvz_real_dreams_marketplace.html | Superadmin | /api/v1/real-dreams/public/property-types<br>/api/v1/real-dreams/public/properties?${params} |
| rvz_real_dreams_partners.html | Superadmin | None detected |
| rvz_real_dreams_properties.html | Superadmin | None detected |
| rvz_sales_revenue.html | Superadmin | None detected |
| superadmin_awards_simple.html | Superadmin | /api/v1/awards/super-admin/awards/<br>/api/v1/awards/super-admin/awards/pending?limit=500 |
| superadmin_global_config.html | Superadmin | None detected |
| superadmin_password_reset.html | Superadmin | None detected |
| superadmin_placement_approvals.html | Superadmin | None detected |
| superadmin_red_id_oversight.html | Superadmin | None detected |
| superadmin_system_health.html | Superadmin | None detected |
| partner_change_password.html | Vendor | None detected |
| partner_commissions.html | Vendor | /api/v1/partner/commissions? |
| partner_dashboard.html | Vendor | /api/v1/promo/cross-auth/generate-partner-to-vgk<br>/api/v1/partner/auth/my-orders?limit=1<br>/api/v1/partner/sales-invoices?date_filter=mtd&per_page=1<br>/api/v1/partner/stock/summary<br>/api/v1/partner/walkins/summary?date_filter=mtd<br>/api/v1/promo/cross-auth/check-vgk-link?partner_code= |
| partner_dispatch.html | Vendor | None detected |
| partner_invoices.html | Vendor | None detected |
| partner_kyc_documents.html | Vendor | None detected |
| partner_login.html | Vendor | None detected |
| partner_marketplace.html | Vendor | None detected |
| partner_master.html | Vendor | /api/v1/partner/admin/partners/${editingPartnerId}/logo<br>/api/v1/partner/partners/${partnerId}/create-vgk-login<br>/api/v1/staff/accounts/companies |
| partner_my_leads.html | Vendor | /api/v1/crm/network-search?q=${encodeURIComponent(q)}&type=staff&limit=10<br>/api/v1/partner/wa-templates<br>/api/v1/crm/unified-my-leads/${leadId}/details?company_id=${companyId}<br>/api/v1/crm/network-search?q=${encodeURIComponent(query)}&limit=10<br>/api/v1/crm/signup/categories<br>/api/v1/staff/accounts/companies<br>/api/v1/crm/unified-my-leads/search-mnr?q=${encodeURIComponent(query)}<br>/api/v1/community-services/admin/active-search?q=${encodeURIComponent(query)}<br>/api/v1/crm/unified-my-leads |
| partner_orders.html | Vendor | None detected |
| partner_order_approval.html | Vendor | None detected |
| partner_order_routing.html | Vendor | None detected |
| partner_payments.html | Vendor | None detected |
| partner_portal_invoices.html | Vendor | None detected |
| partner_portal_orders.html | Vendor | None detected |
| partner_portal_payments.html | Vendor | None detected |
| partner_pricing.html | Vendor | None detected |
| partner_purchases.html | Vendor | None detected |
| partner_revenue_dashboard.html | Vendor | None detected |
| partner_sales_invoices.html | Vendor | /api/v1/partner/sales-invoices/${editingInvoiceId}/coupon<br>/api/v1/partner/sales-invoices<br>/api/v1/partner/stock-items-search?search=${encodeURIComponent(val)}&per_page=12<br>/api/v1/partner/sales-invoices?${getDateParams()}&per_page=1<br>/api/v1/partner/sales-invoices/${id}/confirm<br>/api/v1/partner/sales-invoices/${payingInvoiceId}/payment<br>/api/v1/partner/sales-invoices/${id}<br>/api/v1/partner/coupon-validate?code=${encodeURIComponent(code)}<br>/api/v1/partner/auth/me<br>/api/v1/partner/hsn-search?search=${encodeURIComponent(val)}&per_page=8<br>/api/v1/partner/sales-invoices/${editingInvoiceId}/line-items |
| partner_service.html | Vendor | None detected |
| partner_solar_vendor.html | Vendor | None detected |
| partner_spare_orders.html | Vendor | /api/v1/staff/accounts/companies |
| partner_stock.html | Vendor | None detected |
| partner_support.html | Vendor | None detected |
| partner_vendor_returns.html | Vendor | None detected |
| partner_walkins.html | Vendor | /api/v1/partner/wa-templates<br>/api/v1/partner/walkins<br>/api/v1/partner/walkins/${id}<br>/api/v1/signup-categories/list?company_id=${companyId}<br>/api/v1/partner/walkins/verify-otp<br>/api/v1/partner/vgk/search-referral?q=${encodeURIComponent(q)}<br>/api/v1/partner/auth/me<br>/api/v1/partner/vgk/reset-password/${vgkId}<br>/api/v1/partner/sales-team/search?q=${encodeURIComponent(q)}<br>/api/v1/partner/vgk/check-phone?phone=${encodeURIComponent(phone)}<br>/api/v1/partner/walkins/summary?${buildDateParams()}<br>/api/v1/partner/walkins/send-otp<br>/api/v1/partner/walkins?search=${encodeURIComponent(phone)}&per_page=5 |
| vendor_login.html | Vendor | /api/v1/vendor/auth/login<br>/api/v1/partner/auth/login<br>/api/v1/password-reset/portal/vendor/verify-otp<br>/api/v1/password-reset/portal/vendor/reset-password<br>/api/v1/password-reset/portal/solar_vendor/verify-otp<br>/api/v1/password-reset/portal/vendor/forgot-password<br>/api/v1/password-reset/portal/solar_vendor/forgot-password<br>/api/v1/password-reset/portal/solar_vendor/reset-password |
| vendor_portal.html | Vendor | None detected |
| vendor_scan.html | Vendor | None detected |
