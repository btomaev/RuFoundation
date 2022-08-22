/*
 * test/prop.rs
 *
 * ftml - Library to parse Wikidot text
 * Copyright (C) 2019-2022 Wikijump Team
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

use crate::data::{PageInfo, PageRef, NullPageCallbacks};
use crate::render::{html::HtmlRender, text::TextRender, Render};
use crate::settings::{WikitextMode, WikitextSettings};
use crate::tree::attribute::SAFE_ATTRIBUTES;
use crate::tree::{
    Alignment, AnchorTarget, AttributeMap, ClearFloat, Container, ContainerType, Element,
    FloatAlignment, Heading, HeadingLevel, ImageSource, LinkLabel, LinkLocation,
    LinkType, ListItem, ListType, SyntaxTree,
};
use proptest::option;
use proptest::prelude::*;
use std::borrow::Cow;
use std::num::NonZeroU32;
use std::rc::Rc;

// Constants

lazy_static! {
    static ref SAFE_ATTRIBUTES_VEC: Vec<&'static str> =
        SAFE_ATTRIBUTES.iter().map(|s| s.as_ref()).collect();
}

const SIMPLE_EMAIL_REGEX: &str = r"\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*";
const SIMPLE_URL_REGEX: &str = r"https?://([-.]\w)+";

// Helper macros

macro_rules! select {
    ($items:expr) => {
        proptest::sample::select(&$items[..])
    };
}

macro_rules! cow {
    ($strategy:expr) => {
        $strategy.prop_map(Cow::Owned)
    };
}

// Leaf elements

fn arb_attribute_map() -> impl Strategy<Value = AttributeMap<'static>> {
    proptest::collection::btree_map(
        // Key
        prop_oneof![
            // Safe attribute
            select!(SAFE_ATTRIBUTES_VEC).prop_map(|s| Cow::Owned(str!(s))),
            // Random attribute
            cow!(r"[A-Za-z0-9-]+"),
        ],
        // Value
        cow!(".*"),
        // Length
        0..12,
    )
    .prop_map(|map| AttributeMap::from(map))
}

#[inline]
fn arb_optional_str() -> impl Strategy<Value = Option<Cow<'static, str>>> {
    option::of(cow!(".*"))
}

fn arb_target() -> impl Strategy<Value = Option<AnchorTarget>> {
    option::of(select!([
        AnchorTarget::NewTab,
        AnchorTarget::Parent,
        AnchorTarget::Top,
        AnchorTarget::Same,
    ]))
}

fn arb_page_ref() -> impl Strategy<Value = PageRef<'static>> {
    let site = option::of(cow!(r"[a-z0-9\-]+"));
    let page = cow!(r"[a-z0-9\-_:]+");

    (site, page).prop_map(|(site, page)| PageRef { site, page })
}

fn arb_link_location() -> impl Strategy<Value = LinkLocation<'static>> {
    prop_oneof![
        (arb_page_ref(), option::of(cow!(".*"))).prop_map(|(page_ref, anchor)| LinkLocation::Page(page_ref, anchor)),
        cow!(".+").prop_map(LinkLocation::Url),
    ]
}

fn arb_link_type() -> impl Strategy<Value = LinkType> {
    select!([
        LinkType::Direct,
        LinkType::Page,
        LinkType::Interwiki,
        LinkType::Anchor,
        LinkType::TableOfContents,
    ])
}

fn arb_link_element() -> impl Strategy<Value = Element<'static>> {
    let label = prop_oneof![
        cow!(".*").prop_map(LinkLabel::Text),
        option::of(cow!(SIMPLE_URL_REGEX)).prop_map(LinkLabel::Url),
        Just(LinkLabel::Page),
    ];

    (arb_link_type(), arb_link_location(), label, arb_target()).prop_map(
        |(ltype, link, label, target)| Element::Link {
            ltype,
            link,
            label,
            target,
        },
    )
}

fn arb_image() -> impl Strategy<Value = Element<'static>> {
    let source = prop_oneof![
        cow!(SIMPLE_URL_REGEX).prop_map(ImageSource::Url),
        cow!(".*").prop_map(|file| ImageSource::File1 { file }),
        (cow!(".*"), cow!(".*"))
            .prop_map(|(page, file)| ImageSource::File2 { page, file }),
    ];

    let alignment = select!([
        Alignment::Left,
        Alignment::Right,
        Alignment::Center,
        Alignment::Justify,
    ]);

    let image_alignment = option::of(
        (alignment, any::<bool>())
            .prop_map(|(align, float)| FloatAlignment { align, float }),
    );

    (
        source,
        option::of(arb_link_location()),
        image_alignment,
        arb_attribute_map(),
    )
        .prop_map(|(source, link, alignment, attributes)| Element::Image {
            source,
            link,
            alignment,
            attributes,
        })
}

fn arb_list<S>(elements: S) -> impl Strategy<Value = Element<'static>>
where
    S: Strategy<Value = Vec<Element<'static>>> + 'static,
{
    macro_rules! make_list {
        ($items:expr) => {{
            let ltype = select!([ListType::Bullet, ListType::Numbered]);
            let items = $items;
            let attributes = arb_attribute_map();

            (ltype, items, attributes).prop_map(|(ltype, items, attributes)| {
                Element::List {
                    ltype,
                    items,
                    attributes,
                }
            })
        }};
    }

    let list_item = (elements, arb_attribute_map()).prop_map(|(elements, attributes)| {
        ListItem::Elements {
            hidden: false,
            elements,
            attributes,
        }
    });
    let leaf = make_list!(proptest::collection::vec(list_item, 1..10));

    leaf.prop_recursive(
        5,  // Levels deep
        30, // Number of total nodes
        10, // Up to X items per collection
        |inner| {
            make_list!(inner.prop_map(|element| {
                let element = Box::new(element);
                vec![ListItem::SubList { element }]
            }))
        },
    )
}

fn arb_code() -> impl Strategy<Value = Element<'static>> {
    (cow!(".*"), arb_optional_str())
        .prop_map(|(contents, language)| Element::Code { contents, language })
}

fn arb_checkbox() -> impl Strategy<Value = Element<'static>> {
    (any::<bool>(), arb_attribute_map()).prop_map(|(checked, attributes)| {
        Element::CheckBox {
            checked,
            attributes,
        }
    })
}

// Container elements

fn arb_container<S>(elements: S) -> impl Strategy<Value = Element<'static>>
where
    S: Strategy<Value = Vec<Element<'static>>>,
{
    let alignment = select!([
        Alignment::Left,
        Alignment::Right,
        Alignment::Center,
        Alignment::Justify,
    ]);

    let heading = {
        let has_toc = select!([true, false]);
        let level = select!([
            HeadingLevel::One,
            HeadingLevel::Two,
            HeadingLevel::Three,
            HeadingLevel::Four,
            HeadingLevel::Five,
            HeadingLevel::Six,
        ]);

        (level, has_toc).prop_map(|(level, has_toc)| Heading { level, has_toc })
    };

    let container_type = prop_oneof![
        Just(ContainerType::Bold),
        Just(ContainerType::Italics),
        Just(ContainerType::Underline),
        Just(ContainerType::Superscript),
        Just(ContainerType::Subscript),
        Just(ContainerType::Strikethrough),
        Just(ContainerType::Monospace),
        Just(ContainerType::Span),
        Just(ContainerType::Div),
        Just(ContainerType::Mark),
        Just(ContainerType::Blockquote),
        Just(ContainerType::Insertion),
        Just(ContainerType::Deletion),
        Just(ContainerType::Hidden),
        Just(ContainerType::Invisible),
        Just(ContainerType::Size),
        Just(ContainerType::Paragraph),
        alignment.prop_map(|align| ContainerType::Align(align)),
        heading.prop_map(|heading| ContainerType::Header(heading)),
    ];

    (container_type, elements, arb_attribute_map()).prop_map(
        |(ctype, elements, attributes)| {
            Element::Container(Container::new(ctype, elements, attributes))
        },
    )
}

fn arb_collapsible<S>(elements: S) -> impl Strategy<Value = Element<'static>>
where
    S: Strategy<Value = Vec<Element<'static>>>,
{
    (
        elements,
        arb_attribute_map(),
        any::<bool>(),
        arb_optional_str(),
        arb_optional_str(),
        any::<bool>(),
        any::<bool>(),
    )
        .prop_map(
            |(
                elements,
                attributes,
                start_open,
                show_text,
                hide_text,
                show_top,
                show_bottom,
            )| Element::Collapsible {
                elements,
                attributes,
                start_open,
                show_text,
                hide_text,
                show_top,
                show_bottom,
            },
        )
}

// Syntax Tree

fn arb_element_leaf() -> impl Strategy<Value = Element<'static>> {
    prop_oneof![
        cow!(".*").prop_map(Element::Text),
        cow!(".*").prop_map(Element::Raw),
        cow!(SIMPLE_EMAIL_REGEX).prop_map(Element::Email),
        arb_link_element(),
        arb_image(),
        // TODO: Element::RadioButton
        arb_checkbox(),
        // TODO: Element::User
        arb_code(),
        cow!(".*").prop_map(|contents| Element::Html { contents }),
        // TODO: Element::Iframe
        Just(Element::LineBreak),
        (1..50_u32)
            .prop_map(|count| Element::LineBreaks(NonZeroU32::new(count).unwrap())),
        select!([ClearFloat::Both, ClearFloat::Left, ClearFloat::Right])
            .prop_map(Element::ClearFloat),
        Just(Element::HorizontalRule),
    ]
}

fn arb_tree() -> impl Strategy<Value = SyntaxTree<'static>> {
    let leaf = arb_element_leaf();
    let element = leaf.prop_recursive(
        5,  // Levels deep
        50, // Number of total nodes
        10, // Up to X items per collection
        |inner| {
            // Inner strategy for recursive cases
            macro_rules! elements {
                () => {
                    proptest::collection::vec(inner.clone(), 1..20)
                };
            }

            prop_oneof![
                arb_container(elements!()),
                // TODO: Element::Anchor
                arb_list(elements!()),
                arb_collapsible(elements!()),
                // TODO: Element::IfCategory
                // TODO: Element::IfTags
                // TODO: Element::Color
            ]
        },
    );

    let toc_elements = proptest::collection::vec(arb_element_leaf(), 1..5);
    let toc_heading = arb_list(toc_elements);
    let footnote = proptest::collection::vec(element.clone(), 5..10);
    let internal_link = arb_page_ref();

    (
        proptest::collection::vec(element, 1..100),
        proptest::collection::vec(toc_heading, 0..2),
        any::<bool>(),
        proptest::collection::vec(footnote, 0..2),
        proptest::collection::vec(internal_link, 0..5),
    )
        .prop_map(
            |(elements, table_of_contents, has_toc_block, footnotes, internal_links)| SyntaxTree {
                elements,
                table_of_contents,
                has_toc_block,
                footnotes,
                internal_links,
            },
        )
}

// Page Info

fn arb_page_info() -> impl Strategy<Value = PageInfo<'static>> {
    (
        cow!(".+"),
        arb_optional_str(),
        cow!(".+"),
        cow!(".+"),
        cow!(".+"),
        cow!(".+"),
        arb_optional_str(),
        any::<f64>(),
        proptest::collection::vec(cow!(".+"), 0..20),
        cow!(r"[a-z\-]+"),
    )
        .prop_map(
            |(page, category, site, title, domain, media_domain, alt_title, rating, tags, language)| PageInfo {
                page,
                category,
                site,
                title,
                domain,
                media_domain,
                alt_title,
                rating,
                tags,
                language,
            },
        )
}

// Property Test

fn render<R: Render>(
    render: R,
    tree: SyntaxTree<'static>,
    page_info: PageInfo<'static>,
) -> R::Output {
    let settings = WikitextSettings::from_mode(WikitextMode::Page);
    render.render(&tree, &page_info, Rc::new(NullPageCallbacks{}), &settings)
}

proptest! {
    // Warning: these tests are *very* slow.
    #![proptest_config(ProptestConfig::with_cases(16))]

    #[test]
    #[ignore = "slow test"]
    fn render_html_prop(page_info in arb_page_info(), tree in arb_tree()) {
        let out = render(HtmlRender, tree, page_info);
        assert!(out.meta.len() >= 4);
    }

    #[test]
    #[ignore = "slow test"]
    fn render_text_prop(page_info in arb_page_info(), tree in arb_tree()) {
        let _ = render(TextRender, tree, page_info);
    }
}