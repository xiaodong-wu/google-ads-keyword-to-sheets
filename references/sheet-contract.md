# Spreadsheet contract

## Destination

- Spreadsheet title: `Automatically publish articles`
- Spreadsheet ID: `1n-J4tu5IfiaVQI9496hRzlFNKLwXNQLDQY_HZAf1UmM`
- Spreadsheet URL:
  `https://docs.google.com/spreadsheets/d/1n-J4tu5IfiaVQI9496hRzlFNKLwXNQLDQY_HZAf1UmM/edit`
- Known tab example: `www.nutricdmo.com`

Normalize the user-supplied domain to a lowercase ASCII hostname while preserving `www`. Require an
exact visible tab-title match. Do not create a missing tab. Use this contract only when the user
explicitly supplied a domain; never select the example tab for a no-domain run.

## Required headers

The literal localized values below are part of the existing external spreadsheet schema. Keep them
unchanged even though the skill interface and instructions are English.

Require row 1 columns A:H in this exact order:

1. `核心关键字`
2. `目标国家`
3. `目标客户`
4. `相关产品链接`
5. `发布密钥`
6. `发布状态`
7. `发布时间`
8. `新发布文章链接`

## Row policy

- Select the latest populated row whose C:E cells are all non-empty as the template.
- Append after the last non-empty A cell.
- Populate A with one prepared keyword and B with the user's location text.
- Copy A:E from the template with `PASTE_NORMAL`, then overwrite A:B in the same batch. This
  preserves C:E values and row formatting without handling the publishing key outside Sheets.
- Require F:H to be blank in the destination and leave them untouched.
- Re-read A immediately before writing and deduplicate again.
- Use 500-row maximum chunks. Verify each chunk before starting the next.

Treat column E as secret. It may be read only to establish that a complete template exists and may
be copied only inside the spreadsheet. Never include its value in a local artifact, tool argument,
log, report, or final response.

## Request shapes

Indexes are zero-based, start-inclusive, and end-exclusive. Resolve `sheetId`, template indexes,
destination indexes, and row capacity from fresh metadata and reads.

Append missing grid rows when necessary:

```json
{
  "appendDimension": {
    "sheetId": 0,
    "dimension": "ROWS",
    "length": 250
  }
}
```

Copy one template row across a destination chunk:

```json
{
  "copyPaste": {
    "source": {
      "sheetId": 0,
      "startRowIndex": 69,
      "endRowIndex": 70,
      "startColumnIndex": 0,
      "endColumnIndex": 5
    },
    "destination": {
      "sheetId": 0,
      "startRowIndex": 70,
      "endRowIndex": 120,
      "startColumnIndex": 0,
      "endColumnIndex": 5
    },
    "pasteType": "PASTE_NORMAL",
    "pasteOrientation": "NORMAL"
  }
}
```

Overwrite A:B for the same chunk with an `updateCells` request whose range height equals
`rows.length`, every row contains exactly two `values`, and `fields` is `userEnteredValue`.

## Verification

After every chunk, read A:H with:

`userEnteredValue,effectiveValue,formattedValue,dataValidation,userEnteredFormat`

Verify the exact A/B inputs, non-empty copied C:E cells, blank F:H cells, preserved validation and
formatting, and no unrelated changes. Report only non-secret values and row ranges.
