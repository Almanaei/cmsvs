# Activity Logging Test Guide

This guide explains how to test the new cross-user activity logging functionality in the CMSVS application.

## Overview

The system now allows all users to access and manage any request in the system, while logging all cross-user activities for audit purposes. This test page helps verify that the activity logging is working correctly.

## Accessing the Test Page

1. **Login as an Admin User**
   - The test page is accessible via the admin navigation
   - Navigate to: `/test/activity`
   - Or click "اختبار الأنشطة" in the admin sidebar

2. **Test Page Features**
   - Cross-user activity logging tests
   - Regular activity logging tests
   - Request access simulation
   - Activity viewer for different users

## Test Scenarios

### 1. Cross-User Activity Logging Test

**Purpose**: Test manual logging of cross-user activities

**Steps**:
1. Select a target user from the dropdown
2. Choose an activity type (e.g., "cross_user_request_viewed")
3. Optionally select a specific request
4. Enter a description
5. Click "تسجيل النشاط المتقاطع"

**Expected Result**: Activity should be logged to the target user's activity log

### 2. Regular Activity Logging Test

**Purpose**: Test regular user activity logging

**Steps**:
1. Select an activity type from the dropdown
2. Enter a description
3. Click "تسجيل النشاط العادي"

**Expected Result**: Activity should be logged to your own activity log

### 3. Request Access Simulation

**Purpose**: Simulate real cross-user request access scenarios

**Steps**:
1. Look at the request cards displayed
2. Note which requests belong to you vs. other users
3. Click action buttons (عرض, تعديل, ملفات) on other users' requests
4. Check the response messages

**Expected Results**:
- Cross-user access should be logged automatically
- Own requests should not generate cross-user logs
- Success messages should indicate whether it was cross-user access

### 4. Activity Viewer

**Purpose**: View logged activities for different users

**Steps**:
1. Select a user from the "عرض الأنشطة" dropdown
2. Review the displayed activities
3. Look for activities marked with "متقاطع" (cross-user) or "اختبار" (test)

**Expected Results**:
- Activities should display with proper descriptions
- Cross-user activities should be clearly marked
- Test activities should be identifiable

## Real-World Testing

### Testing Cross-User Request Management

1. **Create Test Users**:
   ```
   User A: Regular user with some requests
   User B: Regular user with some requests
   Admin: Admin user
   ```

2. **Test Scenarios**:

   **Scenario 1: User A accesses User B's request**
   - Login as User A
   - Navigate to User B's request (via direct URL or search)
   - Verify access is granted
   - Check User B's activity log for the access record

   **Scenario 2: User A edits User B's request**
   - Login as User A
   - Edit User B's request
   - Submit changes
   - Check User B's activity log for the edit record

   **Scenario 3: User A downloads files from User B's request**
   - Login as User A
   - Access User B's request files
   - Download a file
   - Check User B's activity log for the file access record

### Verification Steps

1. **Check Activity Logs**:
   - Go to `/admin/activities` or `/admin/requests-records`
   - Filter by user to see their activities
   - Look for cross-user activity entries

2. **Verify Activity Details**:
   - Each cross-user activity should include:
     - Who accessed the request (accessing_user_id, accessing_user_name)
     - What was accessed (request_id, request_number)
     - When it happened (timestamp)
     - How it was accessed (IP address, user agent)
     - Additional context (action type, file names, etc.)

3. **Test Different Activity Types**:
   - `cross_user_request_viewed`: Viewing another user's request
   - `cross_user_request_edited`: Editing another user's request
   - `cross_user_request_status_updated`: Updating another user's request status
   - `cross_user_file_accessed`: Accessing files from another user's request
   - `cross_user_file_deleted`: Deleting files from another user's request

## API Endpoints for Testing

The test page provides these API endpoints:

- `POST /test/activity/log-cross-user`: Manually log cross-user activity
- `POST /test/activity/log-regular`: Manually log regular activity
- `GET /test/activity/user/{user_id}`: Get activities for a specific user
- `GET /test/activity/simulate-cross-user/{request_id}`: Simulate cross-user access

## Expected Activity Log Entries

When User A (أحمد محمد) accesses User B's request, User B's activity log should show:

```
تم عرض الطلب REQ-2024-001 بواسطة أحمد محمد
تم تعديل الطلب REQ-2024-001 بواسطة أحمد محمد
تم تحديث حالة الطلب REQ-2024-001 إلى مكتمل بواسطة أحمد محمد
تم تحميل الملف document.pdf من الطلب REQ-2024-001 بواسطة أحمد محمد
```

## Troubleshooting

### Common Issues

1. **Test page not accessible**:
   - Ensure you're logged in as an admin
   - Check that test routes are properly registered
   - Verify the URL: `/test/activity`

2. **Activities not logging**:
   - Check database connectivity
   - Verify ActivityService is working
   - Check application logs for errors

3. **Cross-user access not working**:
   - Verify permission checks have been removed
   - Check that users can actually access other users' requests
   - Test with different user roles

### Debug Information

The test page includes error handling and will display:
- Success/error messages for each action
- Detailed error information if something fails
- Activity details including metadata

## Security Considerations

While testing, remember:
- This functionality allows any user to access any request
- All access is logged for audit purposes
- The test page should only be available in development/testing environments
- Consider removing or restricting the test page in production

## Next Steps

After testing:
1. Verify all activity types are working correctly
2. Test the admin activity viewing interfaces
3. Ensure proper cleanup of test data if needed
4. Document any issues or improvements needed
5. Consider adding automated tests based on manual test results
