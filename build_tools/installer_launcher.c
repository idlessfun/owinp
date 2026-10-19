/*
 * OWINP installer launcher.
 *
 * Inno Setup always unpacks itself into %TEMP%\is-XXXX.tmp. On machines where
 * %TEMP% is not writable (broken ACL, policy, antivirus) the installer fails
 * with "Access denied" before it can show a single page.
 *
 * This launcher embeds the real installer as a resource, extracts it into a
 * writable folder under %LOCALAPPDATA%\OWINP\installer-temp, passes
 * /TEMP=<that folder> and starts it. No network, no registry, no system paths.
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <stdio.h>

#include "resource.h"

#define CMDLINE_CAP 32768

static void ShowError(const wchar_t *text)
{
    MessageBoxW(NULL, text, L"OWINP Setup", MB_ICONERROR | MB_OK);
}

static BOOL EnsureDirectory(const wchar_t *path)
{
    int result = SHCreateDirectoryExW(NULL, path, NULL);
    return result == ERROR_SUCCESS || result == ERROR_ALREADY_EXISTS;
}

static BOOL ExtractPayload(HINSTANCE instance, const wchar_t *target)
{
    HRSRC resource = FindResourceW(instance, MAKEINTRESOURCEW(IDR_SETUP), RT_RCDATA);
    if (resource == NULL)
        return FALSE;

    DWORD size = SizeofResource(instance, resource);
    HGLOBAL loaded = LoadResource(instance, resource);
    if (loaded == NULL || size == 0)
        return FALSE;

    void *data = LockResource(loaded);
    if (data == NULL)
        return FALSE;

    HANDLE file = CreateFileW(target, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                              FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return FALSE;

    DWORD written = 0;
    BOOL ok = WriteFile(file, data, size, &written, NULL) && written == size;
    CloseHandle(file);

    if (!ok)
        DeleteFileW(target);

    return ok;
}

/* Appends one quoted command-line argument. */
static BOOL AppendArgument(wchar_t *buffer, size_t capacity, const wchar_t *argument)
{
    size_t length = wcslen(buffer);
    if (length + 3 >= capacity)
        return FALSE;

    buffer[length++] = L'"';
    for (const wchar_t *p = argument; *p != L'\0'; ++p)
    {
        if (*p == L'"')
        {
            if (length + 2 >= capacity)
                return FALSE;
            buffer[length++] = L'\\';
        }

        if (length + 2 >= capacity)
            return FALSE;
        buffer[length++] = *p;
    }

    buffer[length++] = L'"';
    buffer[length] = L'\0';
    return TRUE;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR cmdline, int show)
{
    (void)previous;
    (void)cmdline;
    (void)show;

    wchar_t temp_root[MAX_PATH];
    DWORD length = GetEnvironmentVariableW(L"OWINP_INSTALLER_TEMP", temp_root, MAX_PATH);

    if (length == 0 || length >= MAX_PATH)
    {
        wchar_t local_appdata[MAX_PATH];
        if (FAILED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, local_appdata)))
        {
            ShowError(L"Cannot determine the local application data folder.");
            return 2;
        }

        if (swprintf_s(temp_root, MAX_PATH, L"%s\\OWINP\\installer-temp",
                       local_appdata) < 0)
        {
            ShowError(L"The path to the temporary folder is too long.");
            return 2;
        }
    }

    if (!EnsureDirectory(temp_root))
    {
        ShowError(L"Cannot create a writable temporary folder:\n"
                  L"%LOCALAPPDATA%\\OWINP\\installer-temp\n\n"
                  L"Check the permissions of your profile folder.");
        return 2;
    }

    wchar_t core[MAX_PATH];
    if (swprintf_s(core, MAX_PATH, L"%s\\OWINP-Setup-core.exe", temp_root) < 0)
    {
        ShowError(L"The path to the installer is too long.");
        return 2;
    }

    if (!ExtractPayload(instance, core))
    {
        ShowError(L"Cannot unpack the installer into the temporary folder.");
        return 2;
    }

    /* Inno Setup reads TEMP/TMP; /TEMP= makes it use our writable folder too. */
    SetEnvironmentVariableW(L"TEMP", temp_root);
    SetEnvironmentVariableW(L"TMP", temp_root);

    int argc = 0;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argv == NULL)
    {
        ShowError(L"Cannot parse the command line.");
        return 2;
    }

    wchar_t command[CMDLINE_CAP];
    if (swprintf_s(command, CMDLINE_CAP, L"\"%s\" /TEMP=\"%s\"", core, temp_root) < 0)
    {
        LocalFree(argv);
        ShowError(L"The command line is too long.");
        return 2;
    }

    for (int index = 1; index < argc; ++index)
    {
        if (wcscat_s(command, CMDLINE_CAP, L" ") != 0 ||
            !AppendArgument(command, CMDLINE_CAP, argv[index]))
        {
            LocalFree(argv);
            ShowError(L"The command line is too long.");
            return 2;
        }
    }

    LocalFree(argv);

    STARTUPINFOW startup;
    PROCESS_INFORMATION process;
    ZeroMemory(&startup, sizeof(startup));
    ZeroMemory(&process, sizeof(process));
    startup.cb = sizeof(startup);

    if (!CreateProcessW(core, command, NULL, NULL, FALSE, 0, NULL,
                        temp_root, &startup, &process))
    {
        ShowError(L"Cannot start the installer.");
        DeleteFileW(core);
        return 2;
    }

    WaitForSingleObject(process.hProcess, INFINITE);

    DWORD exit_code = 2;
    GetExitCodeProcess(process.hProcess, &exit_code);

    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    DeleteFileW(core);

    return (int)exit_code;
}
